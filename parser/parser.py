from models.graph import Graph
from models.zone import Zone
from models.connection import Connection
from errors import ParseError, MapError
from typing import Any


class ParsedMap:
    """Store the graph and number of drones parsed from a map file."""

    def __init__(self, graph: Graph, nb_drones: int = 0) -> None:
        """Initialize a parsed map.

        Args:
            graph: Graph containing the parsed zones and connections.
            nb_drones: Number of drones declared in the map.
        """
        self.graph: Graph = graph
        self.nb_drones: int = nb_drones


class MapParser:
    """Parse a map file into a Graph and a drone count."""

    def __init__(self, filename: str) -> None:
        """Initialize the parser.

        Args:
            filename: Path to the map file.
        """
        self.filename: str = filename
        self.graph: Graph = Graph()
        self.nb_drones: int | None = None

    def parse(self) -> ParsedMap:
        """Parse the map file and return the resulting map.

        The file must contain the number of drones first, followed by
        zone and connection declarations.

        Returns:
            The ParsedMap containing graph and number of drones.

        Raises:
            ParseError: If the file is empty or contains an invalid entry.
        """
        with open(self.filename, "r") as f:
            first_entry: bool = True
            # HANDLE EMPTY FILE
            content: list[str] = f.readlines()
            if not content:
                raise ParseError(0, "Empty file!")

            # READ LINE BY LINE
            for line_number, line in enumerate(content, start=1):
                line = line.strip()

                # IF EMPTY, COMMENTED OR MALFORMED LINE
                if not line or line.startswith("#"):
                    continue
                if ":" not in line:
                    raise ParseError(line_number, f"Malformed line: '{line}'")

                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # CHECK IF ITS FIRST LINE
                if first_entry:
                    if key != "nb_drones":
                        raise ParseError(
                            line_number,
                            "'Nb_drones' must be the first entry."
                        )
                    first_entry = False
                self.handle_key(key, value, line_number)
        return ParsedMap(self.graph, self.nb_drones)

    def handle_key(self, key: str, value: str, line_number: int) -> None:
        """Handle a line entry according to its key.

        Args:
            key: Type of map entry to process.
            value: Data associated with the entry.
            line_number: Line number of the entry in the map file.

        Raises:
            ParseError: If the entry type is unknown or its data is invalid.
        """
        if key == "nb_drones":
            self.parse_nb_drones(value, line_number)
        elif key in ["start_hub", "end_hub", "hub"]:
            self.handle_zone(key, value, line_number)
        elif key == "connection":
            self.handle_connection(value, line_number)
        else:
            raise ParseError(line_number, f"Unknown entry: {key}")

    def handle_zone(self, key: str, value: str, line_number: int) -> None:
        """
        Handle zones depending on the entry (key)

        Args:
            key (str): entry (hub, start_hub, end_hub)
            value (str): dat from split line
            line_number (int): in case of errors

        Returns:
            None

        Raises:
            ParseError: If the entry type is unknown or its data is invalid.
        """
        zone: Zone = self.parse_zone(key, value)
        try:
            self.graph.add_zone(zone)
            if key == "start_hub":
                self.set_start(zone, line_number)
            elif key == "end_hub":
                self.set_end(zone, line_number)
        except MapError as e:
            raise ParseError(line_number, str(e)) from e

    def handle_connection(self, value: str, line_number: int) -> None:
        """
        Call Connection parser and add it to the graph

        Args:
            value (str): data from the split line
            line_number (int): in case of errors

        Raises:
            ParseError: If the connection is invalid or cannot be added.

        """
        conn: Connection = self.parse_connection(value)
        try:
            self.graph.add_connection(conn)
        except MapError as e:
            raise ParseError(line_number, str(e)) from e

    def set_start(self, zone: Zone, line_number: int) -> None:
        """
        Sets the starting zone of the graph

        Args:
            zone (Zone): zone to set as start
            line_number (int): line number in case of error

        Raises:
            ParseError: If a starting zone was already defined.

        """
        if self.graph.start is not None:
            raise ParseError(
                line_number,
                "Duplicate 'start_hub'!"
            )
        if self.graph.end is not None:
            if (self.graph.end.x == zone.x and
                    self.graph.end.y == zone.y):
                raise ParseError(
                    line_number,
                    "Start/End must have different coordinates!"
                )
        self.graph.start = zone

    def set_end(self, zone: Zone, line_number: int) -> None:
        """
        Sets the end zone of the graph

        Args:
            zone (Zone): zone to set as end
            line_number (int): line number in case of error

        Raises:
            ParseError: If an ending zone was already defined.

        """
        if self.graph.end is not None:
            raise ParseError(
                line_number,
                "Duplicate 'end_hub'!"
            )
        if self.graph.start is not None:
            if (self.graph.start.x == zone.x and
                    self.graph.start.y == zone.y):
                raise ParseError(
                    line_number,
                    "Start/End must have different coordinates!"
                )
        self.graph.end = zone

    def parse_nb_drones(self, value: str, line_number: int) -> None:
        """
        Parse the number of drones from file

        Args:
            value (str): data from the split line
            line_number (int): line n8umber in case of error

        Raises:
            ParseError: If the value is not a positive integer or was already defined.
        """
        if self.nb_drones is not None:
            raise ParseError(
                line_number,
                "'Nb_drones' is mentioned twice."
            )
        try:
            nb_drones: int = int(value)
            if nb_drones <= 0:
                raise ValueError
        except ValueError:
            raise ParseError(
                line_number,
                "nb_drones must be a positive integer"
            )
        self.nb_drones = nb_drones

    def parse_zone(self, key: str, value: str, line_number: int) -> Zone:
        """Parse a zone declaration line into a Zone instance.

        Args:
            key: The zone keyword (`start_hub`, `end_hub`, or `hub`).
            value: contains the zone's name, coordinates, and optional metadata.

        Returns:
            The constructed Zone.

        Raises:
            ParseError: If the zone declaration is invalid.
        """
        if "[" in value:
            if (not value.endswith("]")
                    or value.count("[") != 1
                    or value.count("]") != 1):
                raise ParseError(
                    line_number,
                    "Wrong zone format, usage->  (<prefix>: <name> <x> <y> [metadata-optional])"
                )
            zone_data, metadata = value.split("[", 1)
            parts: list[str] = zone_data.split()
            metadata: str = metadata.rstrip("]")
            meta_parts: list[str] = metadata.split()
        else:
            parts = value.split()
            meta_parts: list[str] = list()

        if len(parts) != 3:
            raise ParseError(
                line_number,
                "Wrong zone format, usage-> (<prefix>: <name> <x> <y> [metadata-optional])"
            )

        name: str = parts[0]
        if "-" in name:
            raise ParseError(line_number, "Name must not contain '-'")

        try:
            x = int(parts[1])
            y = int(parts[2])
        except ValueError:
            raise ParseError(line_number, "Coordinates must be integers.")

        if not meta_parts:
            return Zone(name, x, y)
        return self.parse_zone_metadata(parts, key, meta_parts, line_number)

    def parse_zone_metadata(self, parts: list[str], key: str, meta_parts: list[str], line_number: int) -> Zone:
        for data in meta_parts:
            if not "=" in data:
                raise ParseError(
                    line_number,
                    "Wrong metadata format (Usage: [color=red])")

            meta, meta_value = data.split("=", 1)
            if key in ["start_hub", "end_hub"]:
                if meta not in ["color", "max_drones"]:
                    raise ParseError(
                        line_number, "Wrong metadata format, only 'color', 'max_drones' allowed")
                elif meta == "color":
                    color: str = meta_value
                elif meta == "zone":
                    if meta_value not in ["normal", "restricted", "blocked", "priority"]:
                        raise ParseError(
                            line_number,
                            "Wrong zone type.")
                    zone_type: str = meta_value
                elif meta == "max_drones":
                    try:
                        max_drones: int = int(meta_value)
                        if max_drones <= 0:
                            raise ValueError
                    except ValueError:
                        raise ParseError(
                            line_number, "max_drones value must be a positive integer")
            else:
                if meta not in ["color", "zone", "max_drones"]:
                    raise ParseError(
                        line_number, "Wrong metadata format, only 'color', 'zone', 'max_drones' allowed")

    def parse_connection(self, line: str) -> Connection:
        """Parse a connection declaration line into a Connection instance.

        Args:
            line: The remainder of the line after the `connection:` keyword,
                containing the two zone names and optional metadata.

        Returns:
            The constructed Connection.

        Raises:
            ParseError: If the connection declaration is invalid.
        """
        pass
