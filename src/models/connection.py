from src.models.zone import Zone


class Connection():
    """Represent a bidirectional connection (edge) between two zones."""

    def __init__(
            self,
            zone_a: Zone,
            zone_b: Zone,
            max_link_capacity: int
    ) -> None:
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

    @property
    def name(self) -> str:
        """Return the connection name, e.g. "start-waypoint1".

        Used as the key in the reservation table and in the output of
        drones that are in flight toward a restricted zone.
        """
        return f"{self.zone_a.name}-{self.zone_b.name}"

    def other(self, zone: Zone) -> Zone:
        """Return the zone at the opposite end of this connection.

        Args:
            zone: One of the two zones linked by this connection.

        Returns:
            The zone on the other side.
        """
        return self.zone_b if zone == self.zone_a else self.zone_a
