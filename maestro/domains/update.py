from maestro.domains.entity import Entity, EntityAttribute
from maestro.integrations.home_assistant.types import Domain


class Update(Entity):
    domain = Domain.UPDATE

    auto_update = EntityAttribute(bool)
    installed_version = EntityAttribute(str)
    in_progress = EntityAttribute(bool)
    latest_version = EntityAttribute(str)
    skipped_version = EntityAttribute(str)
    title = EntityAttribute(str)

    def install(self) -> None:
        self.perform_action("install")

    def skip(self) -> None:
        self.perform_action("skip")

    def clear_skipped(self) -> None:
        self.perform_action("clear_skipped")
