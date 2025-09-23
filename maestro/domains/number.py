from maestro.domains.entity import Entity, EntityAttribute
from maestro.integrations.home_assistant.types import Domain


class Number(Entity):
    domain = Domain.NUMBER

    min = EntityAttribute(int)
    max = EntityAttribute(int)
    step = EntityAttribute(int)
    mode = EntityAttribute(str)

    def set_value(self, value: float) -> None:
        self.perform_action("set_value", value=value)
