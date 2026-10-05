"""Positive end-to-end test for the monitoring perception pipeline."""

import cv2

from src.monitoring.monitoring_event import create_monitoring_event
from src.perception.annotation import save_annotated_image
from src.perception.smoke_detector import SmokeDetector


INPUT_IMAGE = "data/perception_test/smoke_test_01.jpg"
OUTPUT_IMAGE = (
    "data/test_outputs/"
    "positive_pipeline_annotated.jpg"
)

SIM_IMAGE_WIDTH = 400
SIM_IMAGE_HEIGHT = 225


def main() -> None:
    """Run a simulator-shaped positive image through the monitoring pipeline."""

    print("[INPUT] Loading known-positive smoke image...")

    image = cv2.imread(INPUT_IMAGE)

    if image is None:
        raise FileNotFoundError(
            f"Could not load test image: {INPUT_IMAGE}"
        )

    # Match the dimensions currently produced by the Project AirSim
    # DownCamera.
    simulator_frame = cv2.resize(
        image,
        (SIM_IMAGE_WIDTH, SIM_IMAGE_HEIGHT),
    )

    print(
        "[INPUT] Simulator-shaped frame created: "
        f"shape={simulator_frame.shape}, "
        f"dtype={simulator_frame.dtype}"
    )

    detector = SmokeDetector(
        confidence_threshold=0.5,
    )

    print("[PERCEPTION] Running smoke detector...")

    result = detector.detect(simulator_frame)

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

    if not result.detected:
        raise AssertionError(
            "Known-positive simulator-shaped image "
            "did not produce a smoke detection."
        )

    print("[MONITORING] Creating MonitoringEvent...")

    event = create_monitoring_event(
        result=result,
        camera_id="camera_1",
        search_region_id="sector_test",
    )

    if event is None:
        raise AssertionError(
            "Positive detection did not produce a MonitoringEvent."
        )

    print("MonitoringEvent created:")
    print(event.to_dict())

    print("[EVIDENCE] Saving annotated image...")

    output_path = save_annotated_image(
        image=simulator_frame,
        result=result,
        output_path=OUTPUT_IMAGE,
    )

    print(f"Annotated evidence saved to: {output_path}")

    print(
        "\n[SUCCESS] Positive simulator-shaped frame "
        "completed the monitoring pipeline."
    )


if __name__ == "__main__":
    main()