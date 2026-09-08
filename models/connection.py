from models.zone import Zone


class Connection():
    def __init__(self, zone_a: Zone, zone_b: Zone, max_capacity: int):
        self.zone_a = zone_a
        self.zone_b = zone_b
        self.max_capacity = max_capacity
