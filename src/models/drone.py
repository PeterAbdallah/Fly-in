from src.models.zone import Zone
from src.models.connection import Connection


class Drone():
    """Represent a single drone moving through the graph."""

    def __init__(self, drone_id: int, current_zone: Zone) -> None:
        """Initialize a drone at its starting zone.

        Args:
            drone_id: The drone's unique identifier.
            current_zone: The zone the drone currently occupies.
        """
        self.drone_id: int = drone_id
        self.current_zone: Zone | None = current_zone
        self.current_connection: Connection | None = None
        self.path: list[tuple[str, int]] | None = None
