from maestro.domains.entity import ON, Entity
from maestro.integrations.home_assistant.domain import Domain


class Switch(Entity):
    domain = Domain.SWITCH
    allow_set_state = False

    @property
    def is_on(self) -> bool:
        return self.state == ON

    def turn_on(self) -> None:
        self.perform_action("turn_on")

    def turn_off(self) -> None:
        self.perform_action("turn_off")

    def toggle(self) -> None:
        self.perform_action("toggle")
