"""Plan drone routes and play them through terminal or graphical views."""

from src.models.drone import Drone
from src.models.zone import Zone
from src.parser.parser import ParsedMap
from src.solving.planner import plan_drone, reserve_path, _find_connection
from src.solving.reservation_table import ReservationTable


class Simulation:
    """Keep planning and drone position updates independent of drawing."""

    def __init__(self, map: ParsedMap) -> None:
        """Create the fleet and shared reservations from a parsed map."""
        self.map: ParsedMap = map
        start = map.graph.start
        end = map.graph.end
        if start is None or end is None:
            raise ValueError("The map must have a start and an end zone.")
        self.start: Zone = start
        self.end: Zone = end
        self.table: ReservationTable = ReservationTable(
            self.start, self.end)
        self.drones: list[Drone] = [Drone(i, self.start)
                                    for i in range(1, map.nb_drones + 1)]
        self.turn: int = 0
        self.total_turns: int = 0

    def plan(self) -> None:
        """Plan every drone and reserve each route before playback."""
        for drone in self.drones:
            # Get drone path
            path = plan_drone(
                self.map.graph,
                self.table,
                self.start,
                self.end
            )

            if path is None:
                raise ValueError(f"No schedule found for D{drone.drone_id}.")
            drone.path = path

            # Reserve the drone path
            reserve_path(
                self.map.graph,
                self.table,
                path
            )

            # Update the max turns required
            self.total_turns = max(
                self.total_turns,
                path[-1][1]
            )

    def step(self) -> str | None:
        """Advance one turn and return its movements, or None when finished."""
        if self.turn >= self.total_turns:
            return None

        self.turn += 1
        movements: list[str] = []
        for drone in self.drones:
            path = drone.path
            if path is None:
                raise ValueError(
                    f"D{drone.drone_id} has no path. Call plan() first."
                )

            for i in range(1, len(path)):
                name_a, turn_a = path[i - 1]
                name_b, turn_b = path[i]
                if not turn_a < self.turn <= turn_b:
                    continue

                # wait
                if name_a == name_b:
                    drone.current_zone = self.map.graph.get_zone(name_b)
                    drone.current_connection = None

                # moving to restricted, standing on connection
                elif self.turn < turn_b:
                    connection = _find_connection(
                        self.map.graph,
                        self.map.graph.get_zone(name_a),
                        self.map.graph.get_zone(name_b)
                    )
                    drone.current_zone = None
                    drone.current_connection = connection
                    movements.append(f"D{drone.drone_id}-{connection.name}")

                # Arrived to destination
                elif self.turn == turn_b:
                    zone = self.map.graph.get_zone(name_b)
                    drone.current_zone = zone
                    drone.current_connection = None
                    movements.append(f"D{drone.drone_id}-{name_b}")
                break
        return " ".join(movements)

    def run(self) -> None:
        """Play positions in the terminal using the same steps as the GUI."""
        while True:
            movements = self.step()
            if movements is None:
                return
            print(movements)
