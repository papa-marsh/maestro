from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Lock(Entity):
    domain = Domain.LOCK

    def lock(self) -> None:
        self.perform_action("lock")

    def unlock(self) -> None:
        self.perform_action("unlock")
