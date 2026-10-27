"""Store a drone's fixed timed route and play it one turn at a time."""

# A drone can occupy a zone or, during restricted travel, a connection.
# Graph lets playback resolve names from the saved path into these objects.
from src.models.zone import Zone
from src.models.connection import Connection
from src.models.graph import Graph
from enum import Enum


class DroneState(Enum):
    """The possible states a drone can be in during the simulation."""

    WAITING = "waiting"
    MOVING = "moving"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"


class Drone():
    """Represent a single drone moving through the graph."""

    def __init__(self, drone_id: int, current_zone: Zone) -> None:
        """Initialize a drone at its starting zone.

        Args:
            drone_id: The drone's unique identifier.
            current_zone: The zone the drone currently occupies.
        """
        self.drone_id = drone_id
        self.current_zone: Zone | None = current_zone
        self.current_connection: Connection | None = None
        self.state: DroneState = DroneState.WAITING
        self.path: list[tuple[str, int]] = []
        # Index 0 is the start; index 1 is the first planned action.
        # Keep this index on a restricted move until its arrival turn occurs.
        self._next_step: int = 1

    def assign_path(self, graph: Graph,
                    path: list[tuple[str, int]]) -> None:
        """Store a timed path and reset the drone to its starting state."""
        # Even a route with no travel must contain its initial position.
        if not path:
            raise ValueError("A drone path must contain a starting state.")
        # Replacing the route and resetting the index also supports restarting.
        self.path = path
        self._next_step = 1
        # Start playback at the first saved zone, with no in-flight connection.
        self.current_zone = graph.get_zone(path[0][0])
        self.current_connection = None
        # A one-state route already starts at its destination and is delivered.
        self.state = (
            DroneState.DELIVERED if len(path) == 1 else DroneState.WAITING
        )

    def advance(self, graph: Graph, turn: int) -> str | None:
        """Apply the next simulation turn and return a movement destination.

        Call once per turn, starting at turn 1. Waiting and delivered drones
        return None; a drone in transit returns its connection's name.

        This method follows the assigned path. It does not call the planner,
        choose neighbors, change reservations, or recompute arrival times.
        """
        # An exhausted route has no further movement to print or animate.
        if self._next_step >= len(self.path):
            return None

        # Read the last reached zone and the next zone's scheduled arrival.
        # "_" discards the departure time because arrival controls this step.
        source, _ = self.path[self._next_step - 1]
        destination, arrival = self.path[self._next_step]

        if turn < arrival:
            # A two-turn entry has one intermediate turn on the connection.
            # Keep _next_step unchanged so the next call lands at this same
            # destination. The drone cannot wait extra turns in mid-flight.
            source_zone = graph.get_zone(source)
            for connection in graph.get_neighbors(source_zone):
                # Connections are bidirectional; other() finds either endpoint.
                if connection.other(source_zone).name == destination:
                    self.current_connection = connection
                    self.current_zone = None
                    self.state = DroneState.IN_TRANSIT
                    # Reverse trips also use this connection's stored name.
                    return connection.name
            # A planner-produced move must connect adjacent zones. Report a
            # corrupt route clearly instead of pretending that the drone moved.
            raise ValueError(f"No connection from {source} to {destination}.")

        # The scheduled arrival turn is here: consume this state and land.
        self._next_step += 1
        self.current_zone = graph.get_zone(destination)
        self.current_connection = None
        if source == destination:
            # Repeating a zone at a later turn means WAIT, not a new move.
            # Returning None tells Simulation to omit it from the movement log.
            self.state = DroneState.WAITING
            return None

        # Print the final arrival once. Later calls see an exhausted path and
        # produce no more tokens for this delivered drone.
        self.state = (
            DroneState.DELIVERED
            if self.current_zone is graph.end else DroneState.MOVING
        )
        # Simulation adds "D<ID>-"; Drone reports only where it went.
        return destination
