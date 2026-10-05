"""Monitoring event creation from perception results."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional

from src.perception.smoke_detector import DetectionResult


@dataclass
class MonitoringEvent:
    """Event produced when passive monitoring warrants investigation."""

    camera_id: str
    timestamp: str
    event_type: str
    confidence: float
    image_bbox: tuple[int, int, int, int]
    search_region_id: str

    def to_dict(self) -> dict:
        """Return the event as a serializable dictionary."""
        return asdict(self)


def create_monitoring_event(
    result: DetectionResult,
    camera_id: str,
    search_region_id: str,
    timestamp: Optional[datetime] = None,
) -> Optional[MonitoringEvent]:
    """Create a monitoring event from a positive smoke detection.

    Returns None when the detector found no smoke.
    """

    if not result.detected:
        return None

    # If multiple smoke detections exist, use the highest-confidence
    # detection as the primary trigger for the monitoring event.
    primary_detection = max(
        result.detections,
        key=lambda detection: detection.confidence,
    )

    event_timestamp = timestamp or datetime.now()

    return MonitoringEvent(
        camera_id=camera_id,
        timestamp=event_timestamp.isoformat(timespec="seconds"),
        event_type="suspected_smoke",
        confidence=primary_detection.confidence,
        image_bbox=primary_detection.bbox,
        search_region_id=search_region_id,
    )