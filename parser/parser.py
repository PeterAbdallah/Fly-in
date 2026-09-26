from models.graph import Graph
from models.zone import Zone
from models.connection import Connection
from errors import ParseError, MapError


class ParsedMap:
    """Container for the fully-parsed result of a map file."""

    def __init__(self, graph: Graph, nb_drones: int = 0) -> None:
        """Initialize the parsed map.

        Args:
            graph: The graph built from the zones and connections in the file.
            nb_drones: The number of drones declared in the file.
        """
        self.graph: Graph = graph
        self.nb_drones: int = nb_drones


class MapParser:
    """Parse a map file into a Graph and a drone count."""

    def __init__(self, filename: str) -> None:
        """Initialize the parser for a given file.

        Args:
            filename: Path to the map file to parse.
        """
        self.filename: str = filename
        self.graph: Graph = Graph()
        self.nb_drones: int = 0

    def parse(self) -> ParsedMap:
        """Read and parse the map file line by line.

        Reads `nb_drones`, zone declarations (`start_hub`/`end_hub`/`hub`),
        and `connection` entries, validating each as it goes and building
        up `self.graph` and `self.nb_drones` accordingly. Blank lines and
        `#`-prefixed comments are skipped.

        Returns:
            A ParsedMap wrapping the built graph and drone count.

        Raises:
            ParseError: If any line is malformed, `nb_drones` is missing,
                not first, or invalid, or if a zone/connection declaration
                is semantically invalid (duplicate zone, duplicate start/end,
                unknown zone reference, self-connection, etc.).
        """
        with open(self.filename, "r") as f:
            first_entry: bool = True

            for line_number, line in enumerate(f, start=1):
                line = line.strip()

                if not line or line.startswith("#"):
                    continue
                if ":" not in line:
                    raise ParseError(line_number, f"Malformed line: '{line}'")

                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if first_entry:
                    if key != "nb_drones":
                        raise ParseError(
                            line_number,
                            "'nb_drones' must be the first entry"
                        )
                    first_entry = False

                if key == "nb_drones":
                    try:
                        nb_drones: int = int(value)
                    except ValueError:
                        raise ParseError(
                            line_number,
                            "nb_drones must be an integer"
                            )
                    if nb_drones <= 0:
                        raise ParseError(
                            line_number,
                            "nb_drones must be a positive integer"
                        )
                    self.nb_drones = nb_drones
                elif key in ["start_hub", "end_hub", "hub"]:
                    zone: Zone = self.parse_zone(key, value)
                    try:
                        self.graph.add_zone(zone)
                        if key == "start_hub":
                            self.graph.start = zone
                        elif key == "end_hub":
                            self.graph.end = zone
                    except MapError as e:
                        raise ParseError(line_number, str(e)) from e
                elif key == "connection":
                    conn: Connection = self.parse_connection(value)
                    try:
                        self.graph.add_connection(conn)
                    except MapError as e:
                        raise ParseError(line_number, str(e)) from e
        return ParsedMap(self.graph, self.nb_drones)

    def parse_zone(self, key: str, value: str) -> Zone:
        """Parse a zone declaration line into a Zone instance.

        Args:
            key: The zone keyword (`start_hub`, `end_hub`, or `hub`).
            value: The remainder of the line after the keyword, containing
                the zone's name, coordinates, and optional metadata.

        Returns:
            The constructed Zone.
        """
        pass

    def parse_connection(self, line: str) -> Connection:
        """Parse a connection declaration line into a Connection instance.

        Args:
            line: The remainder of the line after the `connection:` keyword,
                containing the two zone names and optional metadata.

        Returns:
            The constructed Connection.
        """
        pass