"""Drone dispatch logic for inspection requests."""

from src.dispatch.inspection_request import InspectionRequest
from src.dispatch.search_regions import InspectionTarget, resolve_search_region
from src.simulation.projectairsim_adapter import ProjectAirSimAdapter

from dataclasses import dataclass

@dataclass
class DispatchResult:
    """Result of dispatching a drone to an inspection target."""

    target: InspectionTarget
    actual_north: float
    actual_east: float
    actual_down: float
    arrived: bool

class InspectionDispatcher:
    """Dispatch inspection requests to the simulated drone."""

    def __init__(self, adapter: ProjectAirSimAdapter) -> None:
        """Initialize the dispatcher with a simulation adapter."""
        self.adapter = adapter

    def _check_arrival(
        self,
        target: InspectionTarget,
        tolerance: float,
    ) -> DispatchResult:
        """Check whether the drone arrived within tolerance of the target."""

        position = self.adapter.get_sim_position()

        actual_north = position["x"]
        actual_east = position["y"]
        actual_down = position["z"]

        # Calculate errors
        north_error = abs(actual_north - target.north)
        east_error = abs(actual_east - target.east)
        down_error = abs(actual_down - target.down)

        # Confirm arrival within the specified tolerance
        arrived = (
            north_error <= tolerance
            and east_error <= tolerance
            and down_error <= tolerance
        )

        return DispatchResult(
            target=target,
            actual_north=actual_north,
            actual_east=actual_east,
            actual_down=actual_down,
            arrived=arrived,
        )

    async def dispatch(
        self,
        request: InspectionRequest,
        velocity: float = 5.0,
        arrival_tolerance: float = 1.0,
    ) -> DispatchResult:
        """Dispatch the drone to the target for an inspection request.

        Parameters
        ----------
        request : InspectionRequest
            Structured request describing the inspection to perform.

        velocity : float, optional
            Drone travel velocity in meters per second.

        Returns
        -------
        DispatchResult
            The result of the dispatch, including actual position and arrival status.

        Raises
        ------
        ValueError
            If the request's search region cannot be resolved.
        """

        target = resolve_search_region(request.search_region_id)

        print(
            f"[DISPATCH] Inspection requested for "
            f"{request.search_region_id}"
        )

        print(
            "[DISPATCH] Target: "
            f"north={target.north} "
            f"east={target.east} "
            f"down={target.down}"
        )

        print("[DRONE] Moving to inspection target...")

        await self.adapter.move_to_ned(
            north=target.north,
            east=target.east,
            down=target.down,
            velocity=velocity,
        )

        result = self._check_arrival(
            target=target,
            tolerance=arrival_tolerance,
        )

        print("\n[ARRIVAL]")
        print(
            f"Requested: north={target.north:.2f} "
            f"east={target.east:.2f} "
            f"down={target.down:.2f}"
        )
        print(
            f"Actual:    north={result.actual_north:.2f} "
            f"east={result.actual_east:.2f} "
            f"down={result.actual_down:.2f}"
        )
        print(
            f"Error:      north={abs(result.actual_north - target.north):.2f} "
            f"east={abs(result.actual_east - target.east):.2f} "
            f"down={abs(result.actual_down - target.down):.2f}"
        )
        print(f"Tolerance:  ±{arrival_tolerance:.2f} m per axis")

        if result.arrived:
            print("[SUCCESS] Drone arrived at inspection region.")
        else:
            print("[FAILURE] Drone did not arrive within tolerance.")

        return result