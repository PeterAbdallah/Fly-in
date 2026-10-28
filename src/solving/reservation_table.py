from src.models.zone import Zone
from src.models.connection import Connection


class ReservationTable:
    """Track how many drones use each zone and connection at each turn."""

    def __init__(self, start: Zone, end: Zone) -> None:
        """Create an empty table.

        Args:
            start: The start zone (unlimited capacity).
            end: The end zone (unlimited capacity).
        """
        self._zone_usage: dict[tuple[str, int], int] = {}
        self._link_usage: dict[tuple[str, int], int] = {}
        self._unlimited: set[str] = {start.name, end.name}

    def zone_has_room(self, zone: Zone, turn: int) -> bool:
        """Return True if one more drone fits in the zone at this turn.

        Args:
            zone: The zone to check.
            turn: The turn to check.

        Returns:
            True if the zone has room, False otherwise.
        """
        if zone.name in self._unlimited:
            return True
        used = self._zone_usage.get((zone.name, turn), 0)
        return used < zone.max_drones

    def link_has_room(self, connection: Connection, turn: int) -> bool:
        """Return True if one more drone fits on the connection.

        Args:
            connection: The connection to check.
            turn: The turn to check.

        Returns:
            True if the connection has room, False otherwise.
        """
        used = self._link_usage.get((connection.name, turn), 0)
        return used < connection.max_link_capacity

    def reserve_link(self, connection: Connection, turn: int) -> None:
        """Record one drone on the connection at this turn.

        Args:
            connection: The connection to reserve.
            turn: The turn of the reservation.
        """
        key = (connection.name, turn)
        self._link_usage[key] = self._link_usage.get(key, 0) + 1

    def reserve_zone(self, zone: Zone, turn: int) -> None:
        """Record one drone in the zone at this turn.

        Args:
            zone: The zone to reserve.
            turn: The turn of the reservation.
        """
        if zone.name in self._unlimited:
            return
        key = (zone.name, turn)
        self._zone_usage[key] = self._zone_usage.get(key, 0) + 1
