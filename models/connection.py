from models.zone import Zone


class Connection():
    """Represent a bidirectional connection (edge) between two zones."""

    def __init__(self, zone_a: Zone, zone_b: Zone, max_link_capacity: int):
        """Initialize the connection between two zones.

        Args:
            zone_a: One endpoint zone of the connection.
            zone_b: The other endpoint zone of the connection.
            max_capacity: Maximum number of drones that can traverse this
                connection simultaneously.
        """
        self.zone_a = zone_a
        self.zone_b = zone_b
        self.max_link_capacity = max_link_capacity
