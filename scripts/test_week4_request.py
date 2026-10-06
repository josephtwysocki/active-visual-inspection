"""Smoke test for the Week 4 request and region-resolution flow."""

from src.dispatch.inspection_request import create_inspection_request
from src.dispatch.search_regions import resolve_search_region
from src.monitoring.monitoring_event import MonitoringEvent


def main() -> None:
    """Test MonitoringEvent -> InspectionRequest -> InspectionTarget."""

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

    request = create_inspection_request(event)

    print("\n[DISPATCH] InspectionRequest created:")
    print(request.to_dict())

    target = resolve_search_region(request.search_region_id)

    print("\n[REGION] Inspection target resolved:")
    print(
        f"north={target.north}, "
        f"east={target.east}, "
        f"down={target.down}"
    )


if __name__ == "__main__":
    main()