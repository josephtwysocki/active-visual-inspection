"""End-to-end integration test for the Week 4 dispatch flow.

This script proves the following boundary:

MonitoringEvent
    -> InspectionRequest
    -> search-region resolution
    -> drone dispatch
    -> Project AirSim movement
    -> arrival confirmation

The drone is returned home and landed when possible, including when an
error occurs after takeoff.
"""

import asyncio

from src.dispatch.dispatcher import InspectionDispatcher
from src.dispatch.inspection_request import create_inspection_request
from src.monitoring.monitoring_event import MonitoringEvent
from src.simulation.projectairsim_adapter import ProjectAirSimAdapter


SCENE_CONFIG = "scene_basic_drone.jsonc"


async def main() -> None:
    """Run the Week 4 monitoring-to-dispatch integration test."""

    adapter = ProjectAirSimAdapter(
        scene_config=SCENE_CONFIG,
    )

    connected = False
    drone_prepared = False
    took_off = False

    try:
        # --------------------------------------------------------------
        # CREATE SYNTHETIC MONITORING EVENT
        # --------------------------------------------------------------

        print("[MONITORING] Creating synthetic MonitoringEvent...")

        event = MonitoringEvent(
            camera_id="camera_1",
            timestamp="2026-10-06T10:30:00",
            event_type="suspected_smoke",
            confidence=0.70,
            image_bbox=(91, 0, 400, 180),
            search_region_id="sector_test",
        )

        print("[MONITORING] MonitoringEvent created:")
        print(event.to_dict())

        # --------------------------------------------------------------
        # CREATE INSPECTION REQUEST
        # --------------------------------------------------------------

        print("\n[REQUEST] Creating InspectionRequest...")

        request = create_inspection_request(event)

        print("[REQUEST] InspectionRequest created:")
        print(request.to_dict())

        # --------------------------------------------------------------
        # CONNECT TO SIMULATOR
        # --------------------------------------------------------------

        print("\n[SIMULATION] Connecting to Project AirSim...")

        adapter.connect()
        connected = True

        print("[SIMULATION] Connected successfully.")

        # --------------------------------------------------------------
        # PREPARE DRONE
        # --------------------------------------------------------------

        print("\n[DRONE] Preparing drone...")

        adapter.prepare_drone()
        drone_prepared = True

        print("[DRONE] Drone armed and API control enabled.")

        # --------------------------------------------------------------
        # TAKEOFF
        # --------------------------------------------------------------

        print("\n[DRONE] Taking off...")

        await adapter.takeoff()
        took_off = True

        takeoff_position = adapter.get_sim_position()

        print(
            "[DRONE] Position after takeoff: "
            f"x={takeoff_position['x']:.3f}, "
            f"y={takeoff_position['y']:.3f}, "
            f"z={takeoff_position['z']:.3f}"
        )

        # --------------------------------------------------------------
        # DISPATCH
        # --------------------------------------------------------------

        dispatcher = InspectionDispatcher(adapter)

        print("\n[MISSION] Dispatching inspection request...")

        result = await dispatcher.dispatch(
            request=request,
            velocity=5.0,
            arrival_tolerance=1.0,
        )

        # --------------------------------------------------------------
        # VERIFY ARRIVAL
        # --------------------------------------------------------------

        if not result.arrived:
            raise RuntimeError(
                "Drone failed to arrive within tolerance of the "
                "requested inspection target."
            )

        print(
            "\n[WEEK 4 SUCCESS] Monitoring event successfully triggered "
            "drone dispatch to the requested inspection region."
        )

    finally:
        # --------------------------------------------------------------
        # SAFE CLEANUP
        # --------------------------------------------------------------

        if connected and took_off:
            try:
                print("\n[CLEANUP] Returning drone home...")
                await adapter.return_home()
                print("[CLEANUP] Drone returned home.")

            except Exception as exc:
                print(
                    "[CLEANUP WARNING] Could not return drone home: "
                    f"{exc}"
                )

            try:
                print("[CLEANUP] Landing drone...")
                await adapter.land()
                print("[CLEANUP] Drone landed.")

            except Exception as exc:
                print(
                    "[CLEANUP WARNING] Could not land drone: "
                    f"{exc}"
                )

        if connected and drone_prepared:
            try:
                print("[CLEANUP] Releasing drone control...")
                adapter.shutdown_drone()
                print("[CLEANUP] Drone control released.")

            except Exception as exc:
                print(
                    "[CLEANUP WARNING] Could not release drone control: "
                    f"{exc}"
                )

        if connected:
            try:
                print("[CLEANUP] Disconnecting from Project AirSim...")
                adapter.disconnect()
                print("[CLEANUP] Disconnected.")

            except Exception as exc:
                print(
                    "[CLEANUP WARNING] Could not disconnect cleanly: "
                    f"{exc}"
                )


if __name__ == "__main__":
    asyncio.run(main())