"""Validated mission responses linked to their source inspection."""

from dataclasses import asdict, dataclass
from typing import Literal


@dataclass(frozen=True)
class MissionOutcome:
    """Record a response, without asserting danger or notification delivery.

    Evidence, confidence, and operational errors remain on the linked
    InspectionResult. A review outcome records a local request for review;
    it does not mean an alert was delivered or a person responded.
    """

    inspection_id: str
    decision: Literal["terminate", "request_human_review"]
    reason: Literal["no_smoke_observed", "smoke_observed", "inspection_failed"]

    def __post_init__(self) -> None:
        if not isinstance(self.inspection_id, str) or not self.inspection_id.strip():
            raise ValueError("inspection_id must be a nonempty string.")
        valid_pairs = (
            ("terminate", "no_smoke_observed"),
            ("request_human_review", "smoke_observed"),
            ("request_human_review", "inspection_failed"),
        )
        if (self.decision, self.reason) not in valid_pairs:
            raise ValueError("Unsupported mission decision/reason combination.")

    def to_dict(self) -> dict:
        """Return a JSON-serializable payload using existing project conventions."""
        return asdict(self)
