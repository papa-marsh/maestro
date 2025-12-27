from maestro.domains.entity import ON, Entity
from maestro.integrations.home_assistant.domain import Domain


class InputBoolean(Entity):
    domain = Domain.INPUT_BOOLEAN

    @property
    def is_on(self) -> bool:
        return self.state == ON

    def turn_on(self) -> None:
        self.perform_action("turn_on")

    def turn_off(self) -> None:
        self.perform_action("turn_off")

    def toggle(self) -> None:
        self.perform_action("toggle")
