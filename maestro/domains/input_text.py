from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class InputText(Entity):
    domain = Domain.INPUT_SELECT

    def set(self, value: str) -> None:
        self.perform_action("set_value", value=value)
