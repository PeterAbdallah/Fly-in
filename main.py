#!/usr/bin/env python3

from parser.parser import MapParser


def main() -> None:
    try:
        parser = MapParser("test.txt")
        parsed_map = parser.parse()

        print("\n=== Map Parsed Successfully ===\n")

        print(f"Drones: {parsed_map.nb_drones}")

        print("\nZones:")
        for name, zone in parsed_map.graph.zones.items():
            print(
                f"  - {name}: "
                f"({zone.x}, {zone.y}) | "
                f"type={zone.__class__.__name__}"
            )

        print("\nConnections:")
        for connection in parsed_map.graph.connections:
            print(
                f"  - {connection.zone_a.name} <-> {connection.zone_b.name} | "
                f"capacity={connection.max_link_capacity}"
            )

        print("\nSpecial Zones:")
        print(f"  Start: {parsed_map.graph.start.name}")
        print(f"  End:   {parsed_map.graph.end.name}")

        print()
    except Exception as e:
        print(str(e))


if __name__ == "__main__":
    main()
