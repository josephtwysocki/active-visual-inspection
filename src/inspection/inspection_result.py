"""Project-owned results from smoke inspection after drone arrival."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class InspectionResult:
    """Report a new drone observation, without deciding a mission response.

    ``completed`` means evidence was captured, saved, and analyzed. It does
    not describe dispatch success or whether the drone returned home.

    ``detected`` is True for smoke observed, False for no qualifying smoke
    detection, and None when inspection failed. False does not establish
    that the region is safe or that no fire exists.

    ``confidence`` is the highest qualifying smoke detection confidence.
    It is None for negative or failed inspections; the smoke detector does
    not provide a confidence score for absence of smoke.

    ``evidence_path`` identifies the saved, newly captured drone frame.
    A failed inspection may retain this path if saving preceded the error.
    ``error`` describes an inspection failure, rather than a mission decision.
    """

    inspection_id: str
    completed: bool
    detected: bool | None = None
    confidence: float | None = None
    evidence_path: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        """Reject combinations that confuse failed and negative inspections."""
        if not self.inspection_id.strip():
            raise ValueError("inspection_id must not be empty.")

        if self.completed:
            if self.detected is not True and self.detected is not False:
                raise ValueError("Completed inspections require a detection outcome.")
            if not self.evidence_path or not self.evidence_path.strip():
                raise ValueError("Completed inspections require an evidence path.")
            if self.error is not None:
                raise ValueError("Completed inspections cannot contain an error.")
            if self.detected:
                if self.confidence is None or not 0.0 <= self.confidence <= 1.0:
                    raise ValueError("Smoke detections require confidence in [0, 1].")
            elif self.confidence is not None:
                raise ValueError("Negative inspections have no detection confidence.")
        else:
            if self.detected is not None or self.confidence is not None:
                raise ValueError("Failed inspections cannot report a detection outcome.")
            if not self.error or not self.error.strip():
                raise ValueError("Failed inspections require an error description.")

    def to_dict(self) -> dict:
        """Return a JSON-serializable dictionary using project conventions."""
        return asdict(self)
