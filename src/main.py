#!/usr/bin/env python3

from parser.parser import MapParser
from parser.errors import ParseError
from solving.dijkstra import shortest_path
from models.zone import PriorityZone


def main() -> None:
    file: str = "maps/challenger/01_the_impossible_dream.txt"
    parser = MapParser(file)

    try:
        parsed_map = parser.parse()
    except ParseError as e:
        print(f"Error: {e}")
        return

    print("\n=== Map Parsed Successfully ===\n")
    print(f"Drones: {parsed_map.nb_drones}")

    print("\nZones:")
    for name, zone in parsed_map.graph.zones.items():
        print(
            f"  - {name}: ({zone.x}, {zone.y}) | "
            f"type={zone.__class__.__name__}"
        )

    print("\nConnections:")
    for connection in parsed_map.graph.connections:
        print(
            f"  - {connection.zone_a.name} <-> {connection.zone_b.name} | "
            f"capacity={connection.max_link_capacity}"
        )

    start = parsed_map.graph.start
    end = parsed_map.graph.end

    if start is None or end is None:
        print("\nError: Start or end zone is missing.")
        return

    print("\n=== Dijkstra Test ===")
    print(f"Start: {start.name}")
    print(f"End:   {end.name}")

    path = shortest_path(parsed_map.graph, start, end)

    if path is None:
        print("\nNo path exists between start and end.")
        return

    total_cost = sum(zone.entry_cost() for zone in path[1:])
    priority_count = sum(
        isinstance(zone, PriorityZone) for zone in path[1:]
    )

    print("\nShortest Path:")
    print("  " + " -> ".join(zone.name for zone in path))
    print(f"\nTotal cost: {total_cost}")
    print(f"Priority zones: {priority_count}")
    print(f"Zones in path: {len(path)}")


if __name__ == "__main__":
    main()
