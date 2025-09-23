from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import Domain


class InputNumber(Entity):
    domain = Domain.INPUT_SELECT

    def set_value(self, value: float) -> None:
        self.perform_action("set_value", value=value)

    def increment(self) -> None:
        self.perform_action("increment")

    def decrement(self) -> None:
        self.perform_action("decrement")
