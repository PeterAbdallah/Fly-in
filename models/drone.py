from models.zone import Zone
from enum import Enum


class DroneState(Enum):
    WAITING = "waiting"
    MOVING = "moving"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"


class Drone():
    def __init__(self, drone_id: int, current_zone: Zone) -> None:
        self.drone_id = drone_id
        self.current_zone = current_zone
        self.state: DroneState = DroneState.WAITING
