from models.zone import Zone
from models.connection import Connection
import parser.errors as errors


class Graph:
    """Represent the graph of zones and their connections."""

    def __init__(self):
        """Initialize an empty graph with no start or end zone."""
        self.zones: dict[str, Zone] = dict()
        self.connections: list[Connection] = list()
        self._start: Zone | None = None
        self._end: Zone | None = None

    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the graph.

        Args:
            zone: The zone to add.

        Raises:
            DuplicateZoneError: If a zone with the same name already exists.
        """
        if zone.name in self.zones:
            raise errors.DuplicateZoneError()
        for existing_zone in self.zones.values():
            if existing_zone.x == zone.x and existing_zone.y == zone.y:
                raise errors.DuplicateZoneError()
        self.zones[zone.name] = zone

    def add_connection(self, connection: Connection) -> None:
        """Add a connection between two existing zones.

        Args:
            connection: The connection to add.

        Raises:
            NonExistingZoneError: If either zone does not exist in the graph.
            SameZoneConnectionError: If the connection links a zone to itself.
            DuplicateConnectionError: If an equivalent connection already exists.
        """
        if connection.zone_a not in self.zones:
            raise errors.NonExistingZoneError(connection.zone_a)
        if connection.zone_b not in self.zones:
            raise errors.NonExistingZoneError(connection.zone_b)
        if connection.zone_a == connection.zone_b:
            raise errors.SameZoneConnectionError()
        for existing in self.connections:
            if (
                (existing.zone_a == connection.zone_a
                 and existing.zone_b == connection.zone_b)
                or
                (existing.zone_a == connection.zone_b
                 and existing.zone_b == connection.zone_a)
            ):
                raise errors.DuplicateConnectionError()
        self.connections.append(connection)

    def get_neighbors(self, zone: Zone) -> list[Connection]:
        """Return all connections connected to the given zone.

        Args:
            zone: The zone whose connections should be found.

        Returns:
            A list of connections connected to the given zone.
        """
        neigh: list[Connection] = list()
        for connection in self.connections:
            if zone == connection.zone_a or zone == connection.zone_b:
                neigh.append(connection)
        return neigh

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
            The zone designated as the start zone.

        Raises:
            ValueError: If no start zone has been set.
        """
        return self._start

    @property
    def end(self) -> Zone | None:
        """Return the end zone.

        Returns:
            The zone designated as the end zone.

        Raises:
            ValueError: If no end zone has been set.
        """
        return self._end

    @start.setter
    def start(self, start_zone: Zone):
        """Set the start zone.

        Args:
            start_zone: The zone to designate as the start zone.

        Raises:
            DuplicateStartError: If a start zone has already been set.
        """
        if self._start:
            raise errors.DuplicateStartError(start_zone.name)
        self._start = start_zone

    @end.setter
    def end(self, end_zone: Zone):
        """Set the end zone.

        Args:
            end_zone: The zone to designate as the end zone.

        Raises:
            DuplicateEndError: If an end zone has already been set.
        """
        if self._end:
            raise errors.DuplicateEndError(end_zone.name)
        self._end = end_zone
