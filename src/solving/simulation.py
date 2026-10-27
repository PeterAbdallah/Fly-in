"""Plan the entire fleet, then expose the same turns to both display modes."""

# Iterator means run() yields each line without building the whole log.
from collections.abc import Iterator

from src.models.drone import Drone
from src.models.graph import Graph
from src.solving.dijkstra import shortest_path
from src.solving.planner import plan_drone, reserve_path
from src.solving.reservation_table import ReservationTable


class Simulation:
    """Plan a fleet with shared reservations, then play its paths by turn."""

    def __init__(self, graph: Graph, nb_drones: int) -> None:
        """Create numbered drones at the graph's starting zone."""
        # The parser normally guarantees these conditions, but Simulation can
        # also be constructed directly by a test or another program.
        if graph.start is None or graph.end is None:
            raise ValueError("The map must have a start and an end zone.")
        if nb_drones <= 0:
            raise ValueError("The number of drones must be positive.")

        # Cache the shared graph and endpoints used by every drone's search.
        self.graph = graph
        self.start = graph.start
        self.end = graph.end
        # IDs start at 1 to match the subject's D1, D2, ... output format.
        # All drones initially share the unlimited-capacity start zone.
        self.drones = [Drone(i, self.start) for i in range(1, nb_drones + 1)]
        # One table is shared by the whole fleet, so later searches see earlier
        # drones' future zone/connection use rather than planning in isolation.
        self.table = ReservationTable(self.start, self.end)
        # turn is playback progress; total_turns is the plan's final arrival.
        self.turn: int = 0
        self.total_turns: int = 0

    def prepare(self) -> None:
        """Plan the fleet and reset every drone to turn zero for playback."""
        # Find a static route to calculate a safe planning horizon.
        # This route is only a bound: we do NOT force every drone to follow it.
        # plan_drone() searches for each drone's own timed route afterwards.
        base_path = shortest_path(self.graph, self.start, self.end)
        if base_path is None:
            raise ValueError("No path exists between start and end.")
        # Skip the start when summing costs: being there costs no turns.
        base_cost = sum(zone.entry_cost() for zone in base_path[1:])

        # Clear previous reservations and counters so playback can restart.
        self.table = ReservationTable(self.start, self.end)
        self.turn = 0
        self.total_turns = 0
        # Reset each drone and reserve its path before planning the next one.
        # This is sequential planning of simultaneous travel: D2 sees D1's
        # entire schedule, even though both may leave during the same turn.
        for drone in self.drones:
            # A safe fallback is to wait until earlier drones finish, then
            # follow the base path. This also permits schedules beyond 500.
            max_turn = self.total_turns + base_cost
            # The search may choose waiting, a different route, or even a loop.
            # It respects earlier reservations; those earlier plans stay fixed.
            path = plan_drone(
                self.graph, self.table, self.start, self.end, max_turn
            )
            if path is None:
                raise ValueError(f"No schedule found for D{drone.drone_id}.")
            # Store the COMPLETE path before any playback starts. advance() and
            # the visualizer only read it; they do not re-route the drone.
            drone.assign_path(self.graph, path)
            # Book this route immediately so the next drone cannot overfill it.
            reserve_path(self.graph, self.table, path)
            # The longest arrival sets the number of turns needed by the fleet.
            self.total_turns = max(self.total_turns, path[-1][1])

    def step(self) -> str | None:
        """Advance one turn after prepare(); return None when finished.

        Return the same movement line as run(), including an empty string
        when every drone waits. The caller decides when to print the line.
        """
        # Stop without changing the final state after all drones arrive.
        if self.turn >= self.total_turns:
            return None

        # Advance every drone together by exactly one whole simulation turn.
        # Playback does not check/re-plan conflicts here: prepare() already
        # checked and reserved every action, including committed transit.
        self.turn += 1
        movements: list[str] = []
        for drone in self.drones:
            destination = drone.advance(self.graph, self.turn)
            if destination is not None:
                # A destination can be a zone or a restricted-transit link.
                movements.append(f"D{drone.drone_id}-{destination}")
        # Spaces separate drones; the caller prints one newline per turn.
        return " ".join(movements)

    def run(self) -> Iterator[str]:
        """Prepare the fleet and yield its movement lines until finished."""
        # Use the same preparation and single-turn API as graphical playback.
        # Each new run() starts from zero instead of resuming an old iterator.
        self.prepare()
        while True:
            movements = self.step()
            # None signals completion; an empty line still represents a turn.
            if movements is None:
                return
            # yield pauses here until the caller requests another turn.
            yield movements
