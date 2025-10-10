from enum import IntEnum

from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Fan(Entity):
    domain = Domain.FAN

    class Speed(IntEnum):
        LOW = 33
        MEDIUM = 66
        HIGH = 100

    def turn_on(self) -> None:
        self.perform_action("turn_on")

    def turn_off(self) -> None:
        self.perform_action("turn_off")

    def toggle(self) -> None:
        self.perform_action("toggle")

    def set_speed(self, speed: Speed) -> None:
        self.perform_action("set_percentage", percentage=speed)
