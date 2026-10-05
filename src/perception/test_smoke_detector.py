from src.monitoring.monitoring_event import create_monitoring_event
from src.perception.annotation import save_annotated_image
from src.perception.smoke_detector import SmokeDetector


detector = SmokeDetector(confidence_threshold=0.5)

result = detector.detect(
    "data/perception_test/smoke_test_01.jpg" # Known, obvious smoke
    # "data/perception_test/smoke_test_02.jpg" # Known, obvious smoke
    # "data/perception_test/smoke_test_03.jpg" # Known, obvious smoke
    # "data/perception_test/smoke_test_04.jpg" # Clear sky image. No smoke expected
)

print(f"Smoke detected: {result.detected}")
print(f"Image size: {result.image_width}x{result.image_height}")

for detection in result.detections:
    print(
        f"Label: {detection.label} | "
        f"Confidence: {detection.confidence:.3f} | "
        f"BBox: {detection.bbox}"
    )

event = create_monitoring_event(
    result=result,
    camera_id="camera_1",
    search_region_id="sector_test",
)

if event:
    print("\nMonitoringEvent created:")
    print(event.to_dict())
    # Save annotated image for visual inspection
    output_path = save_annotated_image(
        image="data/perception_test/smoke_test_01.jpg",
        result=result,
        output_path="data/test_outputs/smoke_test_01_annotated.jpg",
    )

    print(f"Annotated image saved to: {output_path}")
else:
    print("\nNo MonitoringEvent created.")