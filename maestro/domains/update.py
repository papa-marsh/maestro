from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Update(Entity):
    domain = Domain.UPDATE

    def install(self) -> None:
        self.perform_action("install")

    def skip(self) -> None:
        self.perform_action("skip")

    def clear_skipped(self) -> None:
        self.perform_action("clear_skipped")
