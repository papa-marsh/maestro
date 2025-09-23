from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import Domain


class InputSelect(Entity):
    domain = Domain.INPUT_SELECT

    def select_first(self) -> None:
        self.perform_action("select_first")

    def select_last(self) -> None:
        self.perform_action("select_last")

    def select_next(self) -> None:
        self.perform_action("select_next")

    def select_previous(self) -> None:
        self.perform_action("select_previous")

    def select_option(self, option: str) -> None:
        self.perform_action("select_option", option=option)

    def set_options(self, options: list[str]) -> None:
        self.perform_action("set_options", options=options)
