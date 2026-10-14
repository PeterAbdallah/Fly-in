#!/usr/bin/env python3

from src.parser.parser import MapParser
from src.parser.errors import ParseError
from src.solving.dijkstra import shortest_path
from src.solving.reservation_table import ReservationTable  # adjust path
from src.models.connection import Connection
from src.models.graph import Graph
from src.models.zone import PriorityZone, Zone, BlockedZone


def test_all(graph: Graph, start: Zone, end: Zone) -> None:
    """Fill every zone and connection to capacity and check it is full."""
    print("\n=== All Zones and Connections Test ===")
    table = ReservationTable(start, end)

    print("\nZones:")
    for zone in graph.zones.values():
        if isinstance(zone, BlockedZone):
            print(f"  [SKIP] {zone.name} (blocked)")
            continue
        if zone in (start, end):
            for _ in range(10):
                table.reserve_zone(zone, 1)
            check(f"{zone.name} unlimited after 10 drones",
                  table.zone_has_room(zone, 1), True)
            continue
        check(f"{zone.name} empty has room",
              table.zone_has_room(zone, 1), True)
        for _ in range(zone.max_drones):
            table.reserve_zone(zone, 1)
        check(f"{zone.name} full at {zone.max_drones} drone(s)",
              table.zone_has_room(zone, 1), False)

    print("\nConnections:")
    for connection in graph.connections:
        check(f"{connection.name} empty has room",
              table.link_has_room(connection, 1), True)
        for _ in range(connection.max_link_capacity):
            table.reserve_link(connection, 1)
        check(f"{connection.name} full at {connection.max_link_capacity}",
              table.link_has_room(connection, 1), False)


def check(label: str, actual: bool, expected: bool) -> None:
    """Print PASS or FAIL for one check."""
    status = "PASS" if actual == expected else "FAIL"
    print(f"  [{status}] {label} (got {actual}, expected {expected})")


def find_connection(graph: Graph, name_a: str, name_b: str) -> Connection:
    """Return the connection between two zones, given their names."""
    zone_a = graph.get_zone(name_a)
    zone_b = graph.get_zone(name_b)
    for connection in graph.get_neighbors(zone_a):
        if connection.other(zone_a) == zone_b:
            return connection
    raise KeyError(f"no connection between {name_a} and {name_b}")


def test_reservation_table(graph: Graph, start: Zone, end: Zone) -> None:
    """Test the reservation table on the real map."""
    print("\n=== Reservation Table Test ===")
    table = ReservationTable(start, end)

    # Link start-A has max_link_capacity=2
    link_sa = find_connection(graph, "start", "A")
    print(f"\nLink {link_sa.name} (capacity {link_sa.max_link_capacity}):")
    check("room at turn 1 (empty)", table.link_has_room(link_sa, 1), True)
    table.reserve_link(link_sa, 1)
    check("room at turn 1 (1/2 used)", table.link_has_room(link_sa, 1), True)
    table.reserve_link(link_sa, 1)
    check("room at turn 1 (2/2 used)", table.link_has_room(link_sa, 1), False)
    check("room at turn 2 (other turn)", table.link_has_room(link_sa, 2), True)

    # Link start-D has the default capacity of 1
    link_sd = find_connection(graph, "start", "D")
    print(f"\nLink {link_sd.name} (capacity {link_sd.max_link_capacity}):")
    check("room at turn 1 (empty)", table.link_has_room(link_sd, 1), True)
    table.reserve_link(link_sd, 1)
    check("room at turn 1 (1/1 used)", table.link_has_room(link_sd, 1), False)
    check(
        "link start-A unaffected",
        table.link_has_room(link_sa, 3),
        True,
    )

    # Zone A has max_drones=2
    zone_a = graph.get_zone("A")
    print(f"\nZone A (max_drones {zone_a.max_drones}):")
    check("room at turn 1 (empty)", table.zone_has_room(zone_a, 1), True)
    table.reserve_zone(zone_a, 1)
    check("room at turn 1 (1/2 used)", table.zone_has_room(zone_a, 1), True)
    table.reserve_zone(zone_a, 1)
    check("room at turn 1 (2/2 used)", table.zone_has_room(zone_a, 1), False)
    check("room at turn 2 (other turn)", table.zone_has_room(zone_a, 2), True)

    # Zone D has the default max_drones of 1
    zone_d = graph.get_zone("D")
    print(f"\nZone D (max_drones {zone_d.max_drones}):")
    check("room at turn 3 (empty)", table.zone_has_room(zone_d, 3), True)
    table.reserve_zone(zone_d, 3)
    check("room at turn 3 (1/1 used)", table.zone_has_room(zone_d, 3), False)

    # Start and end are unlimited
    print("\nUnlimited zones:")
    for _ in range(10):
        table.reserve_zone(end, 5)
        table.reserve_zone(start, 0)
    check("end has room at turn 5", table.zone_has_room(end, 5), True)
    check("start has room at turn 0", table.zone_has_room(start, 0), True)


def main() -> None:
    file: str = "test.txt"
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
            f"  - {connection.name} | "
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
    else:
        total_cost = sum(zone.entry_cost() for zone in path[1:])
        priority_count = sum(
            isinstance(zone, PriorityZone) for zone in path[1:]
        )
        print("\nShortest Path:")
        print("  " + " -> ".join(zone.name for zone in path))
        print(f"\nTotal cost: {total_cost}")
        print(f"Priority zones: {priority_count}")
        print(f"Zones in path: {len(path)}")

    test_reservation_table(parsed_map.graph, start, end)
    test_all(parsed_map.graph, start, end)


if __name__ == "__main__":
    main()
