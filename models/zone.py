from abc import abstractmethod, ABC


class Zone(ABC):
    def __init__(self, name: str, x: int, y: int,
                 color: str | None, max_drones: int):
        self.name = name
        self.x = x
        self.y = y
        self.color = color
        self.max_drones = max_drones

    @abstractmethod
    def entry_cost(self) -> int:
        pass


class NormalZone(Zone):
    def entry_cost(self) -> int:
        return 1


class PriorityZone(Zone):
    def entry_cost(self) -> int:
        return 1


class RestrictedZone(Zone):
    def entry_cost(self) -> int:
        return 2


class BlockedZone(Zone):
    def entry_cost(self) -> int:
        raise ValueError("Blocked zones cannot be entered")
