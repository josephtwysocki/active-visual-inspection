"""Verify Project AirSim RGB frames are compatible with perception."""

import time

from src.monitoring.monitoring_event import create_monitoring_event
from src.perception.annotation import save_annotated_image
from src.perception.smoke_detector import SmokeDetector
from src.simulation.projectairsim_adapter import ProjectAirSimAdapter


SCENE_CONFIG = "scene_basic_drone.jsonc"


def main() -> None:
    """Capture a Project AirSim frame and run it through perception."""

    adapter = ProjectAirSimAdapter(
        scene_config=SCENE_CONFIG,
    )

    detector = SmokeDetector(
        confidence_threshold=0.5,
    )

    try:
        print("[SIM] Connecting to Project AirSim...")
        adapter.connect()

        print("[CAMERA] Starting RGB camera...")
        adapter.start_rgb_camera()

        # Camera messages arrive asynchronously, so give the subscription
        # a short period to receive its first frame.
        frame = None

        for _ in range(20):
            frame = adapter.get_drone_rgb()

            if frame is not None:
                break

            time.sleep(0.25)

        if frame is None:
            raise RuntimeError(
                "No RGB frame received from Project AirSim."
            )

        print(
            f"[CAMERA] RGB frame received: "
            f"shape={frame.shape}, dtype={frame.dtype}"
        )

        print("[PERCEPTION] Running smoke detector...")

        result = detector.detect(frame)

        print(f"Smoke detected: {result.detected}")
        print(
            f"Image size: "
            f"{result.image_width}x{result.image_height}"
        )

        for detection in result.detections:
            print(
                f"Label: {detection.label} | "
                f"Confidence: {detection.confidence:.3f} | "
                f"BBox: {detection.bbox}"
            )

        event = create_monitoring_event(
            result=result,
            camera_id="drone_down_camera",
            search_region_id="sector_test",
        )

        if event:
            print("\nMonitoringEvent created:")
            print(event.to_dict())

            output_path = save_annotated_image(
                image=frame,
                result=result,
                output_path=(
                    "data/test_outputs/"
                    "projectairsim_detection_annotated.jpg"
                ),
            )

            print(
                f"Annotated evidence saved to: {output_path}"
            )

        else:
            print("\nNo MonitoringEvent created.")

    finally:
        print("[SIM] Disconnecting...")
        adapter.disconnect()

    print("\n[SUCCESS] Project AirSim frame passed through perception.")


if __name__ == "__main__":
    main()