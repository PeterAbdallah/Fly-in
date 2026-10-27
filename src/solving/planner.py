"""Search timed routes and reserve the final route chosen for each drone."""

# A heap always removes the smallest tuple, giving the earliest turn first.
import heapq

from src.models.connection import Connection
from src.models.graph import Graph
from src.models.zone import BlockedZone, PriorityZone, Zone
from src.solving.reservation_table import ReservationTable

# Different turns in the same zone are different search states. Therefore a
# path may wait in a zone or return later without repeating a timed state.
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
    # Compare (arrival turn, negative priority count, zone name) left to right.
    # Negating the count makes MORE priority entries sort before fewer entries.
    # Names settle final ties consistently without comparing Zone objects.
    # Move count is NOT part of this score: equally fast routes can keep a
    # forward/backward detour instead of waiting. Loops are allowed.
    heap: list[tuple[int, int, str]] = []
    # For each (zone, turn), retain the best negative priority score found.
    best: dict[State, int] = {}
    # Previous-state links let us reconstruct only the chosen route at the end.
    came_from: dict[State, State] = {}
    # Finalized states need not be expanded again, even if still in the heap.
    done: set[State] = set()

    # Every drone begins at turn zero. Delayed departures are planned as waits.
    first: State = (start.name, 0)
    best[first] = 0
    heapq.heappush(heap, (0, 0, start.name))

    while heap:
        # Explore the earliest queued state. Heap order resolves score ties.
        turn, neg_prio, name = heapq.heappop(heap)
        state: State = (name, turn)
        if state in done:
            continue
        done.add(state)

        if name == end.name:
            # Build the full fixed path before the simulation starts moving.
            return _rebuild(came_from, first, state)

        if turn >= max_turn:
            # Stop expanding this branch so the time-expanded search is finite.
            continue

        current: Zone = graph.get_zone(name)

        # Collect feasible waits/moves first, then update search scores below.
        options: list[tuple[Zone, int]] = []

        if table.zone_has_room(current, turn + 1):
            # Waiting occupies this same zone at the next turn, without a link.
            options.append((current, turn + 1))

        # Undirected connections allow both forward and backward travel.
        for connection in graph.get_neighbors(current):
            neighbor = connection.other(current)

            if isinstance(neighbor, BlockedZone):
                # Check the type before entry_cost(), which raises for blocked.
                continue

            arrival: int = turn + neighbor.entry_cost()
            # Normal/priority entry takes one turn; restricted entry takes two.
            # Only the arrival turn occupies the destination zone.
            if not table.zone_has_room(neighbor, arrival):
                continue

            # Check every travel turn INCLUDING arrival, matching reserve_path.
            # Without +1 the range is empty for a normal one-turn move.
            link_free = all(
                table.link_has_room(connection, t)
                for t in range(turn + 1, arrival + 1)
            )
            if link_free:
                options.append((neighbor, arrival))

        for zone, arrival in options:
            new_state: State = (zone.name, arrival)
            # Entering a priority zone earns a bonus; waiting there does not.
            # Re-entering it later earns another bonus under the current score,
            # which can also favor some loops when final arrival times tie.
            bonus = 1 if (
                zone.name != name and isinstance(zone, PriorityZone)
            ) else 0
            new_neg = neg_prio - bonus
            if new_state in best and best[new_state] <= new_neg:
                # Equal scores retain the FIRST discovered route. There is no
                # preference for fewer moves, so a later equal waiting route
                # does not replace an already recorded out-and-back route.
                continue
            best[new_state] = new_neg
            # Saving the predecessor here fixes which equal-score route wins.
            came_from[new_state] = state
            heapq.heappush(heap, (arrival, new_neg, zone.name))

    return None  # heap empty, end not reached


def _rebuild(
    came_from: dict[State, State], first: State, last: State
) -> list[State]:
    """Follow came_from backwards from the last state to the first."""
    # This walks the SEARCH HISTORY backwards, not the drone during playback.
    states: list[State] = [last]
    while states[-1] != first:
        states.append(came_from[states[-1]])
    states.reverse()
    # Return chronological order so the first state is always (start, 0).
    return states


def _find_connection(graph: Graph, zone_a: Zone, zone_b: Zone) -> Connection:
    """Return the connection between two adjacent zones."""
    # Looking up the actual undirected object keeps both directions on the
    # same capacity counter and uses its stored name in restricted-flight logs.
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
    # zip with a one-state offset gives every consecutive action in the route.
    # Reserve only the chosen path. Trial branches book no capacity.
    for (name_a, turn_a), (name_b, turn_b) in zip(states, states[1:]):
        zone_b = graph.get_zone(name_b)
        if name_a != name_b:  # a move, not a wait
            connection = _find_connection(
                graph, graph.get_zone(name_a), zone_b
            )
            # A restricted move occupies the connection for both travel turns.
            for t in range(turn_a + 1, turn_b + 1):
                table.reserve_link(connection, t)
        # Both a wait and a move occupy the arrival zone on their final turn.
        # The table itself exempts start/end from zone-capacity limits.
        table.reserve_zone(zone_b, turn_b)
