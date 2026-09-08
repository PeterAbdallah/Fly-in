from models.graph import Graph
from models.zone import Zone
from models.connection import Connection
from errors import ParseError


class ParsedMap:
    def __init__(self, graph: Graph, nb_drones: int = 0) -> None:
        self.graph: Graph = graph
        self.nb_drones: int = nb_drones


class MapParser:
    def __init__(self, filename: str):
        self.filename: str = filename
        self.graph: Graph = Graph()
        self.nb_drones: int = 0

    def parse(self) -> ParsedMap:
        with open(self.filename, "r") as f:
            first_entry: bool = True

            for line_number, line in enumerate(f, start=1):
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

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
                    nb_drones: int = int(value)
                    if nb_drones <= 0:
                        raise ParseError(
                            line_number,
                            "nb_drones must be a positive integer"
                        )
                    self.nb_drones = nb_drones
                elif key in ["start_hub", "end_hub", "hub"]:
                    zone: Zone = self.parse_zone(key, value)
                    self.graph.add_zone(zone)
                    if key == "start_hub":
                        self.graph.start = zone
                    elif key == "end_hub":
                        self.graph.end = zone
                elif key == "connection":
                    conn: Connection = self.parse_connection(value)
                    self.graph.add_connection(conn)
        return ParsedMap(self.graph, self.nb_drones)

    def parse_zone(self, key: str, value: str) -> Zone:
        pass

    def parse_connection(self, line: str) -> Connection:
        pass
