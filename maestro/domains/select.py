from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Select(Entity):
    domain = Domain.SELECT

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
