from maestro.domains.entity import ON, Entity
from maestro.integrations.home_assistant.domain import Domain


class Update(Entity):
    domain = Domain.UPDATE
    allow_set_state = False

    @property
    def is_on(self) -> bool:
        return self.state == ON

    def install(self) -> None:
        self.perform_action("install")

    def skip(self) -> None:
        self.perform_action("skip")

    def clear_skipped(self) -> None:
        self.perform_action("clear_skipped")
