from abc import abstractmethod, ABC


class Zone(ABC):
    """Abstract base class for a zone (node) in the map graph."""

    def __init__(self, name: str, x: int, y: int,
                 color: str | None, max_drones: int):
        """Initialize the zone's shared attributes.

        Args:
            name: The zone's unique name.
            x: The zone's x-coordinate.
            y: The zone's y-coordinate.
            color: Optional color used for visual representation.
            max_drones: Maximum number of drones the zone can hold at once.
        """
        self.name = name
        self.x = x
        self.y = y
        self.color = color
        self.max_drones = max_drones

    @abstractmethod
    def entry_cost(self) -> int:
        """Return the cost, in turns, of moving into this zone."""
        pass


class NormalZone(Zone):
    """Standard zone with the default entry cost."""

    def entry_cost(self) -> int:
        """Return the entry cost for a normal zone (1 turn)."""
        return 1


class PriorityZone(Zone):
    """Preferred zone: same cost as normal, but favored in pathfinding."""

    def entry_cost(self) -> int:
        """Return the entry cost for a priority zone (1 turn)."""
        return 1


class RestrictedZone(Zone):
    """Sensitive/dangerous zone that takes longer to enter."""

    def entry_cost(self) -> int:
        """Return the entry cost for a restricted zone (2 turns)."""
        return 2


class BlockedZone(Zone):
    """Inaccessible zone that must never be entered."""

    def entry_cost(self) -> int:
        """Raise, since a blocked zone can never be entered.

        Raises:
            ValueError: Always — blocked zones have no valid entry cost.
        """
        raise ValueError("Blocked zones cannot be entered")