from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import Domain


class Humidifier(Entity):
    domain = Domain.HUMIDIFIER

    def turn_on(self) -> None:
        self.perform_action("turn_on")

    def turn_off(self) -> None:
        self.perform_action("turn_off")

    def toggle(self) -> None:
        self.perform_action("toggle")

    def set_humidity_target(self, target: int) -> None:
        self.perform_action("set_humidity", target=target)
