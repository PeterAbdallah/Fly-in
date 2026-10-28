from src.models.zone import Zone
from src.models.connection import Connection
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
        self.drone_id: int = drone_id
        self.state: DroneState = DroneState.WAITING
        self.current_zone: Zone | None = current_zone
        self.current_connection: Connection | None = None
        self.path: list[tuple[str, int]] | None = None
