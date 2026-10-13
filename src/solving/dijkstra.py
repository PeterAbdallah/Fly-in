import heapq

from models.graph import Graph
from models.zone import Zone, PriorityZone, BlockedZone


def shortest_path(graph: Graph, start: Zone, end: Zone) -> list[Zone] | None:
    """Find the cheapest path between two zones using Dijkstra.

    Among paths of equal cost, the one passing through the most priority
    zones is preferred.

    Args:
        graph: The graph to search.
        start: The zone to start from.
        end: The zone to reach.

    Returns:
        The list of zones from start to end (both included), or None if
        the end zone cannot be reached.
    """
    # Step 1: the heap. Items are (cost, -priority_count, zone_name).
    # Python compares tuples left to right, so cost decides first. On a
    # tie, the more negative number wins, which means MORE priority zones.
    # Names (strings) go in the heap, not Zone objects, so that Python
    # never has to compare two Zone objects.
    heap: list[tuple[int, int, str]] = []

    # Step 2: the notebook. Best known (cost, -priority_count) per zone.
    best: dict[str, tuple[int, int]] = {}

    # Step 3: how we reached each zone on its best route.
    came_from: dict[str, str] = {}

    # Step 4: the start zone costs 0, so push it and note it.
    best[start.name] = (0, 0)
    heapq.heappush(heap, (0, 0, start.name))

    while heap:
        # Step 5: take the cheapest item out of the heap.
        cost, neg_prio, current_name = heapq.heappop(heap)

        # Step 6: reached the end, so rebuild the path (Steps 12 and 13).
        if current_name == end.name:
            return _rebuild_path(graph, came_from, start, end)

        # Step 7: stale entry. A cheaper one for this zone was already
        # handled, so skip this one.
        if (cost, neg_prio) > best[current_name]:
            continue

        current: Zone = graph.get_zone(current_name)

        # Step 8: look at every connection touching the current zone.
        for connection in graph.get_neighbors(current):
            neighbor: Zone = connection.other(current)

            # Blocked zones can never be entered.
            if isinstance(neighbor, BlockedZone):
                continue

            # Step 9: cost of the route that goes through current.
            new_cost = cost + neighbor.entry_cost()
            new_neg_prio = neg_prio - (
                1 if isinstance(neighbor, PriorityZone) else 0
            )
            candidate = (new_cost, new_neg_prio)

            # Step 10: is it better than what the notebook says?
            # A zone never seen before counts as infinitely expensive.
            if neighbor.name not in best or candidate < best[neighbor.name]:
                best[neighbor.name] = candidate
                came_from[neighbor.name] = current_name
                heapq.heappush(
                    heap, (new_cost, new_neg_prio, neighbor.name)
                )

    return None


def _rebuild_path(
    graph: Graph,
    came_from: dict[str, str],
    start: Zone,
    end: Zone,
) -> list[Zone]:
    """Follow came_from backwards from end to start.

    Args:
        graph: The graph, used to turn zone names back into Zone objects.
        came_from: For each zone name, the name of the zone before it.
        start: The start zone.
        end: The end zone.

    Returns:
        The zones from start to end, in travel order.
    """
    # Step 12: walk backwards from the end until we hit the start.
    names: list[str] = [end.name]
    while names[-1] != start.name:
        names.append(came_from[names[-1]])
    names.reverse()

    # Step 13: turn the names back into Zone objects.
    return [graph.get_zone(name) for name in names]
