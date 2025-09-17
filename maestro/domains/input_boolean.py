from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import Domain


class InputBoolean(Entity):
    domain = Domain.INPUT_BOOLEAN

    def turn_on(self) -> None:
        self.perform_action("turn_on")

    def turn_off(self) -> None:
        self.perform_action("turn_off")

    def toggle(self) -> None:
        self.perform_action("toggle")
