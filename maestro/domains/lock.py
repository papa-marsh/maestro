from maestro.domains.entity import Entity, EntityAttribute
from maestro.integrations.home_assistant.types import Domain


class Lock(Entity):
    domain = Domain.LOCK

    def lock(self) -> None:
        self.perform_action("lock")

    def unlock(self) -> None:
        self.perform_action("unlock")