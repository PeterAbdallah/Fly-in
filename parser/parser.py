from models.graph import Graph
from models.zone import Zone, RestrictedZone, PriorityZone, BlockedZone
from models.connection import Connection
from errors import ParseError, MapError


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

        The first non-empty, non-comment entry must declare the number
        of drones.

        Returns:
            A ParsedMap containing the parsed graph and number of drones.

        Raises:
            ParseError: If the file is empty, missing required entries,
                or contains an invalid entry.
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
            if self.nb_drones is None:
                raise ParseError(0, "nb_drones is not specified")
            if self.graph.start is None or self.graph.end is None:
                raise ParseError(0, "Start/End not specified")
        return ParsedMap(self.graph, self.nb_drones)

    def handle_key(self, key: str, value: str, line_number: int) -> None:
        """Handle a map entry according to its key.

        Args:
            key: Type of map entry to process.
            value: Data associated with the entry.
            line_number: Line number of the entry.

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

        Raises:
            ParseError: If the zone is invalid, has duplicate coordinates, or cannot be added to the graph.
        """
        zone: Zone = self.parse_zone(key, value, line_number)
        # check if coordinates already exist
        for existing_zone in self.graph.zones.values():
            if existing_zone.x == zone.x and existing_zone.y == zone.y:
                raise ParseError(
                    line_number,
                    "Two zones cannot have the same coordinates.")
        try:
            self.graph.add_zone(zone)
            if key == "start_hub":
                self.set_start(zone, line_number)
            elif key == "end_hub":
                self.set_end(zone, line_number)
        except MapError as e:
            raise ParseError(line_number, str(e)) from e

    def handle_connection(self, value: str, line_number: int) -> None:
        """Parse and add a connection to the graph.

        Args:
            value: Connection data containing the zone names and optional
                metadata.
            line_number: Line number of the connection declaration.

        Raises:
            ParseError: If the connection is invalid or cannot be added
                to the graph.
        """
        conn: Connection = self.parse_connection(value, line_number)
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
            value: Zone name, coordinates, and optional metadata.
            line_number: Line number of the zone declaration.

        Returns:
            The constructed Zone.

        Raises:
            ParseError: If the zone format, name, coordinates, or metadata is invalid.
        """
        if "[" in value or "]" in value:
            if (not value.endswith("]")
                    or value.count("[") != 1
                    or value.count("]") != 1):
                raise ParseError(
                    line_number,
                    "Wrong zone format, usage->  (<prefix>: <name> <x> <y> [metadata-optional])"
                )
            zone_data, meta_line = value.split("[", 1)
            parts: list[str] = zone_data.split()
            meta_line: str = meta_line.rstrip("]")
            if not meta_line.strip():
                raise ParseError(line_number, "Metadata cannot be empty.")
            meta_parts: list[str] = meta_line.split()
        else:
            parts = value.split()
            meta_parts: list[str] = list()

        if len(parts) != 3:
            raise ParseError(
                line_number,
                "Wrong zone format!\nUsage-> (<prefix>: <name> <x> <y> [metadata-optional])"
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

        zone, color, max_drones = self.parse_zone_metadata(
            key, meta_parts, line_number)
        return self.create_zone(name, x, y, zone, color, max_drones)

    def parse_zone_metadata(self, key: str, meta_parts: list[str], line_number: int) -> tuple[str, str | None, int]:
        """Parse and validate zone metadata.

        Args:
            key: The zone keyword (`start_hub`, `end_hub`, or `hub`).
            meta_parts: Individual metadata fields from the metadata block.
            line_number: Line number of the zone declaration.

        Returns:
            A tuple containing the zone type, color, and maximum number
            of drones.

        Raises:
            ParseError: If metadata is invalid, duplicated, missing a value, or specifies an invalid zone type.
        """
        occurred: dict[str, bool] = {"color": False,
                                     "zone": False,
                                     "max_drones": False}
        # DEFAULT VALUES
        color: str | None = None
        zone: str = "normal"
        max_drones: int = 1

        # LOOP THROUGH METADATA
        for data in meta_parts:
            # IF THERES NO "="
            if not "=" in data:
                raise ParseError(
                    line_number,
                    "Wrong metadata format (Usage: [color=red])")

            meta, meta_value = data.split("=", 1)
            if not meta_value:
                raise ParseError(line_number, f"{meta} does not have a value.")
            if meta not in ["color", "max_drones", "zone"]:
                raise ParseError(
                    line_number,
                    "Wrong metadata format, only 'zone', 'color', and 'max_drones' allowed")

            # COLOR METADATA
            elif meta == "color":
                if occurred["color"]:
                    raise ParseError(
                        line_number,
                        "color metadata written twice!")
                color = meta_value
                occurred["color"] = True

            # MAX_DRONES METADATA
            elif meta == "max_drones":
                if occurred["max_drones"]:
                    raise ParseError(
                        line_number,
                        "max_drones metadata written twice!")
                max_drones = self.validate_max_drones(
                    line_number, meta_value)
                occurred["max_drones"] = True

            # ZONE METADATA
            elif meta == "zone":
                if occurred["zone"]:
                    raise ParseError(
                        line_number, "zone metadata written twice!")
                if meta_value not in ["normal", "restricted", "blocked", "priority"]:
                    raise ParseError(
                        line_number, "Wrong zone type.")
                zone = meta_value
                occurred["zone"] = True
                if key in ["start_hub", "end_hub"] and zone == "blocked":
                    raise ParseError(
                        line_number,
                        "Start/End cannot be blocked!")
        return (zone, color, max_drones)

    @staticmethod
    def validate_max_drones(line_number: int, meta_value: str) -> int:
        """Validate and convert a maximum drone capacity value.

        Args:
            line_number: Line number of the zone declaration.
            meta_value: Maximum number of drones allowed in the zone.

        Returns:
            The validated maximum number of drones.

        Raises:
            ParseError: If the value is not a positive integer.
        """
        try:
            max_drones: int = int(meta_value)
            if max_drones <= 0:
                raise ValueError
            return max_drones
        except ValueError:
            raise ParseError(
                line_number,
                "max_drones value must be a positive integer")

    @staticmethod
    def create_zone(name: str, x: int, y: int, zone_type: str, color: str | None, max_drones: int) -> Zone:
        """Create the appropriate zone instance from its type.

        Args:
            name: Name of the zone.
            x: X-coordinate of the zone.
            y: Y-coordinate of the zone.
            zone_type: Type of zone to create.
            color: Optional zone color.
            max_drones: Maximum number of drones allowed in the zone.

        Returns:
            A Zone instance corresponding to the specified zone type.

        Raises:
            ParseError: If the zone type is invalid.
        """
        if zone_type == "normal":
            return Zone(name, x, y, color, max_drones)
        elif zone_type == "restricted":
            return RestrictedZone(name, x, y, color, max_drones)
        elif zone_type == "blocked":
            return BlockedZone(name, x, y, color, max_drones)
        elif zone_type == "priority":
            return PriorityZone(name, x, y, color, max_drones)
        else:
            raise ParseError(0, "Wrong zone type")

    def parse_connection(self, line: str, line_number: int) -> Connection:
        """Parse a connection declaration line into a Connection instance.

        Args:
            line: The remainder of the line after the `connection:` keyword,
                containing the two zone names and optional metadata.

        Returns:
            The constructed Connection.

        Raises:
            ParseError: If the connection format, zone names, or metadata is invalid.
        """
        pass
