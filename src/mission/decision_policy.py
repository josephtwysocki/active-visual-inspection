"""Deterministic responses to completed or failed smoke inspections."""

from src.inspection.inspection_result import InspectionResult
from src.mission.mission_outcome import MissionOutcome


def evaluate_inspection(result: InspectionResult) -> MissionOutcome:
    """Apply the Week 6 policy without I/O or an additional score threshold.

    Unsupported or malformed input raises; it never defaults to termination.
    A negative observation does not establish safety. Smoke is not a fire-type
    classification, and a failed inspection leaves the observation unknown.
    """
    if not isinstance(result, InspectionResult):
        raise TypeError("Mission policy requires an InspectionResult.")
    # The current result constructor uses truthiness for completed, so enforce
    # the actual bool contract here before accepting a policy input.
    if type(result.completed) is not bool:
        raise ValueError("InspectionResult.completed must be a bool.")
    InspectionResult(**result.to_dict())

    if result.completed is False and result.detected is None:
        decision, reason = "request_human_review", "inspection_failed"
    elif result.completed is True and result.detected is True:
        decision, reason = "request_human_review", "smoke_observed"
    elif result.completed is True and result.detected is False:
        decision, reason = "terminate", "no_smoke_observed"
    else:
        raise ValueError("Unsupported inspection state.")
    return MissionOutcome(result.inspection_id, decision, reason)
