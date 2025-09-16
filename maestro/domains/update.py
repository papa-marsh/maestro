from maestro.domains.entity import Entity, EntityAttribute
from maestro.integrations.home_assistant.types import Domain


class Update(Entity):
    domain = Domain.UPDATE

    def install(self) -> None:
        self.perform_action("install")