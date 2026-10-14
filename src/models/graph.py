from src.models.zone import Zone
from src.models.connection import Connection
import src.parser.errors as errors


class Graph:
    """Represent the graph of zones and their connections."""

    def __init__(self) -> None:
        """Initialize an empty graph with no start or end zone."""
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []
        self._adjacency: dict[str, list[Connection]] = {}
        self._start: Zone | None = None
        self._end: Zone | None = None

    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the graph.

        Args:
            zone: The zone to add.

        Raises:
            DuplicateZoneError: If a zone with the same name or the same
                coordinates already exists.
        """
        if zone.name in self.zones:
            raise errors.DuplicateZoneError()
        for existing_zone in self.zones.values():
            if existing_zone.x == zone.x and existing_zone.y == zone.y:
                raise errors.DuplicateZoneError()
        self.zones[zone.name] = zone
        self._adjacency[zone.name] = []

    def add_connection(self, connection: Connection) -> None:
        """Add a connection between two existing zones.

        Args:
            connection: The connection to add.

        Raises:
            DuplicateConnectionError: If an equivalent connection already
                exists.
        """
        for existing in self._adjacency.get(connection.zone_a.name, []):
            if existing.other(connection.zone_a) == connection.zone_b:
                raise errors.DuplicateConnectionError()
        self.connections.append(connection)
        self._adjacency.setdefault(connection.zone_a.name, []).append(
            connection
        )
        self._adjacency.setdefault(connection.zone_b.name, []).append(
            connection
        )

    def get_neighbors(self, zone: Zone) -> list[Connection]:
        """Return all connections attached to the given zone.

        Args:
            zone: The zone whose connections should be found.

        Returns:
            A list of connections attached to the given zone. Use
            Connection.other(zone) to get the zone on the other side.
        """
        return list(self._adjacency.get(zone.name, []))

    def get_zone(self, name: str) -> Zone:
        """Return a zone by its name.

        Args:
            name: The name of the zone to retrieve.

        Returns:
            The zone with the specified name.

        Raises:
            KeyError: If no zone with the given name exists.
        """
        return self.zones[name]

    @property
    def start(self) -> Zone | None:
        """Return the start zone.

        Returns:
            The zone designated as the start zone, or None if not set.
        """
        return self._start

    @start.setter
    def start(self, start_zone: Zone) -> None:
        """Set the start zone.

        Args:
            start_zone: The zone to designate as the start zone.

        Raises:
            DuplicateStartError: If a start zone has already been set.
        """
        if self._start is not None:
            raise errors.DuplicateStartError(start_zone.name)
        self._start = start_zone

    @property
    def end(self) -> Zone | None:
        """Return the end zone.

        Returns:
            The zone designated as the end zone, or None if not set.
        """
        return self._end

    @end.setter
    def end(self, end_zone: Zone) -> None:
        """Set the end zone.

        Args:
            end_zone: The zone to designate as the end zone.

        Raises:
            DuplicateEndError: If an end zone has already been set.
        """
        if self._end is not None:
            raise errors.DuplicateEndError(end_zone.name)
        self._end = end_zone
