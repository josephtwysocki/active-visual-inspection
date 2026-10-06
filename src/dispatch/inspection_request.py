"""Inspection request structures for drone dispatch."""

from dataclasses import asdict, dataclass
from uuid import uuid4

from src.monitoring.monitoring_event import MonitoringEvent


@dataclass
class InspectionRequest:
    """Request for the drone to investigate a monitoring event."""

    inspection_id: str
    source_event: MonitoringEvent
    reason: str
    search_region_id: str

    def to_dict(self) -> dict:
        """Return the request as a serializable dictionary."""
        return asdict(self)


def create_inspection_request(
    event: MonitoringEvent,
) -> InspectionRequest:
    """Create an inspection request from a monitoring event."""

    return InspectionRequest(
        inspection_id=f"inspection_{uuid4().hex[:8]}",
        source_event=event,
        reason=event.event_type,
        search_region_id=event.search_region_id,
    )