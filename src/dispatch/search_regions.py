"""Search-region definitions for inspection dispatch."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InspectionTarget:
    """Known NED position associated with a monitoring search region."""

    north: float
    east: float
    down: float


SEARCH_REGIONS: dict[str, InspectionTarget] = {
    "sector_test": InspectionTarget(
        north=5.0,
        east=10.0,
        down=-5.0,
    ),
}


def resolve_search_region(search_region_id: str) -> InspectionTarget:
    """Resolve a monitoring search region to its inspection target.

    Parameters
    ----------
    search_region_id : str
        Project-owned identifier for the monitoring region.

    Returns
    -------
    InspectionTarget
        Predefined NED inspection position for the region.

    Raises
    ------
    ValueError
        If the requested search region is not defined.
    """

    try:
        return SEARCH_REGIONS[search_region_id]
    except KeyError as exc:
        raise ValueError(
            f"Unknown search region: {search_region_id!r}"
        ) from exc