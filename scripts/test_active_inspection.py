"""Live Week 5 integration: dispatch, capture, perception, result, and cleanup.

Run from the project root with Blocks open and ROBOFLOW_API_KEY set:
    python -m scripts.test_active_inspection
"""

import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from src.dispatch.dispatcher import InspectionDispatcher
from src.dispatch.inspection_request import create_inspection_request
from src.dispatch.search_regions import resolve_search_region
from src.inspection.inspector import Inspector
from src.monitoring.monitoring_event import MonitoringEvent
from src.perception.smoke_detector import SmokeDetector
from src.simulation.projectairsim_adapter import ProjectAirSimAdapter


async def main() -> None:
    print("[MONITORING] Creating a synthetic trigger; inspection evidence will be real.")
    event = MonitoringEvent(
        camera_id="camera_1",
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        event_type="suspected_smoke",
        confidence=0.70,
        image_bbox=(91, 0, 400, 180),
        search_region_id="sector_test",
    )
    request = create_inspection_request(event)
    print(f"[REQUEST] {request.inspection_id}")

    # Fail before any flight if the region or detector configuration is invalid.
    resolve_search_region(request.search_region_id)
    detector = SmokeDetector()
    adapter = ProjectAirSimAdapter(scene_config="scene_basic_drone.jsonc")
    dispatcher = InspectionDispatcher(adapter)
    output_dir = Path("data/test_outputs/inspections")
    inspector = Inspector(adapter, detector, output_dir)

    preparation_attempted = False
    takeoff_attempted = False
    cleanup_errors: list[str] = []

    try:
        print("[CONNECT] Connecting to Project AirSim...")
        adapter.connect()
        preparation_attempted = True
        adapter.prepare_drone()
        adapter.start_rgb_camera()

        print("[TAKEOFF] Taking off...")
        takeoff_attempted = True
        await adapter.takeoff()

        dispatch_result = await dispatcher.dispatch(
            request, velocity=5.0, arrival_tolerance=1.0
        )
        print("[INSPECTION] Acquiring and analyzing new drone evidence...")
        result = await inspector.inspect(request, dispatch_result)
        print("[RESULT]")
        print(json.dumps(result.to_dict(), indent=2))

        output_dir.mkdir(parents=True, exist_ok=True)
        trace_path = output_dir / f"{request.inspection_id}_trace.json"
        trace = {
            "synthetic_monitoring_trigger": True,
            "inspection_evidence_source": "Project AirSim DownCamera",
            "request": request.to_dict(),
            "dispatch": asdict(dispatch_result),
            "inspection": result.to_dict(),
        }
        trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
        print(f"[TRACE] {trace_path}")

        if not result.completed:
            raise RuntimeError(f"Active inspection failed: {result.error}")
        if result.inspection_id != request.inspection_id:
            raise RuntimeError("Inspection result lost its request identifier.")
        if not result.evidence_path or not Path(result.evidence_path).is_file():
            raise RuntimeError("Inspection evidence file is missing.")

    finally:
        # A partially failed takeoff may still leave the drone airborne.
        # Attempt landing even when returning home fails. Never disarm after
        # a failed landing. Cleanup errors must not hide the primary failure.
        landed = not takeoff_attempted
        if takeoff_attempted:
            print("[RETURN] Returning home...")
            try:
                await adapter.return_home()
            except Exception as exc:
                cleanup_errors.append(f"Return home failed: {exc}")

            print("[LAND] Landing...")
            try:
                await adapter.land()
                landed = True
            except Exception as exc:
                cleanup_errors.append(f"Landing failed: {exc}")

        if preparation_attempted and landed:
            try:
                adapter.shutdown_drone()
            except Exception as exc:
                cleanup_errors.append(f"Drone shutdown failed: {exc}")

        try:
            adapter.disconnect()
        except Exception as exc:
            cleanup_errors.append(f"Disconnect failed: {exc}")

        for error in cleanup_errors:
            print(f"[CLEANUP ERROR] {error}")
        if not cleanup_errors:
            print("[CLEANUP] Complete.")

    if cleanup_errors:
        raise RuntimeError("Integration cleanup failed; see cleanup errors above.")
    print("[PASS] Active inspection completed; evidence saved; drone returned and landed.")


if __name__ == "__main__":
    asyncio.run(main())
