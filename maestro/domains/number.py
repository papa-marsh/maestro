from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import Domain


class Number(Entity):
    domain = Domain.NUMBER

    def set_value(self, value: float) -> None:
        self.perform_action("set_value", value=value)
