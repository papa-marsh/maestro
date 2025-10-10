from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Number(Entity):
    domain = Domain.NUMBER

    def set_value(self, value: float) -> None:
        self.perform_action("set_value", value=value)
