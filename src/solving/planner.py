import heapq

from src.models.connection import Connection
from src.models.graph import Graph
from src.models.zone import BlockedZone, PriorityZone, Zone
from src.solving.reservation_table import ReservationTable

State = tuple[str, int]  # (zone name, turn)


def plan_drone(
    graph: Graph,
    table: ReservationTable,
    start: Zone,
    end: Zone,
    max_turn: int = 500,
) -> list[State] | None:
    """Find the earliest conflict-free path for one drone.

    The search runs over (zone, turn) states. A drone can wait in a zone
    or move to a neighbor, as long as the reservation table has room.

    Args:
        graph: The graph to search.
        table: The reservations of the drones already planned.
        start: The zone the drone starts in (at turn 0).
        end: The zone the drone must reach.
        max_turn: Give up when the search goes past this turn.

    Returns:
        The list of (zone name, turn) states from start to end, or None
        if no valid path was found.
    """
    # turn, neg_priority, name
    heap: list[tuple[int, int, str]] = []
    # (zone, turn) with highest priority
    best: dict[State, int] = {}
    came_from: dict[State, State] = {}
    done: set[State] = set()

    first: State = (start.name, 0)
    best[first] = 0
    heapq.heappush(heap, (0, 0, start.name))

    while heap:
        # Step 6
        turn, neg_prio, name = heapq.heappop(heap)
        state: State = (name, turn)
        if state in done:
            continue
        done.add(state)

        # Step 7
        if name == end.name:
            return _rebuild(came_from, first, state)

        # Step 8
        if turn >= max_turn:
            continue

        current: Zone = graph.get_zone(name)

        # Step 9: collect every valid (zone, arrival turn) option
        options: list[tuple[Zone, int]] = []

        if table.zone_has_room(current, turn + 1):
            options.append((current, turn + 1))          # wait

        for connection in graph.get_neighbors(current):
            neighbor = connection.other(current)
            if isinstance(neighbor, BlockedZone):
                continue
            arrival: int = turn + neighbor.entry_cost()
            if not table.zone_has_room(neighbor, arrival):
                continue
            # The link is used on every turn of the trip (1 or 2 turns)
            link_free = all(
                table.link_has_room(connection, t)
                for t in range(turn + 1, arrival + 1)
            )
            if link_free:
                options.append((neighbor, arrival))      # move

        # Step 10
        for zone, arrival in options:
            new_state: State = (zone.name, arrival)
            bonus = 1 if (
                zone.name != name and isinstance(zone, PriorityZone)
            ) else 0
            new_neg = neg_prio - bonus
            if new_state in best and best[new_state] <= new_neg:
                continue
            best[new_state] = new_neg
            came_from[new_state] = state
            heapq.heappush(heap, (arrival, new_neg, zone.name))

    return None  # Step 11: heap empty, no schedule found


def _rebuild(
    came_from: dict[State, State], first: State, last: State
) -> list[State]:
    """Follow came_from backwards from the last state to the first."""
    states: list[State] = [last]
    while states[-1] != first:
        states.append(came_from[states[-1]])
    states.reverse()
    return states


def _find_connection(graph: Graph, zone_a: Zone, zone_b: Zone) -> Connection:
    """Return the connection between two adjacent zones."""
    for connection in graph.get_neighbors(zone_a):
        if connection.other(zone_a) == zone_b:
            return connection
    raise KeyError(f"no connection between {zone_a.name} and {zone_b.name}")


def reserve_path(
    graph: Graph, table: ReservationTable, states: list[State]
) -> None:
    """Write a finished plan into the reservation table.

    Args:
        graph: The graph the plan was made on.
        table: The table to update.
        states: The path returned by plan_drone.
    """
    for (name_a, turn_a), (name_b, turn_b) in zip(states, states[1:]):
        zone_b = graph.get_zone(name_b)
        if name_a != name_b:  # a move, not a wait
            connection = _find_connection(
                graph, graph.get_zone(name_a), zone_b
            )
            for t in range(turn_a + 1, turn_b + 1):
                table.reserve_link(connection, t)
        table.reserve_zone(zone_b, turn_b)
