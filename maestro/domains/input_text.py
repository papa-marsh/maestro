from maestro.domains.entity import Entity, EntityAttribute
from maestro.integrations.home_assistant.types import Domain


class InputText(Entity):
    domain = Domain.INPUT_SELECT

    min = EntityAttribute(int)
    max = EntityAttribute(int)
    mode = EntityAttribute(str)

    def set(self, value: str) -> None:
        self.perform_action("set_value", value=value)
