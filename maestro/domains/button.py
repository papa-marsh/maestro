from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import Domain


class Button(Entity):
    domain = Domain.BUTTON

    def press(self) -> None:
        self.perform_action("press")
