from maestro.config import NOTIFY_ACTION_MAPPINGS
from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain
from maestro.utils.push import Notif


class Person(Entity):
    domain = Domain.PERSON

    @property
    def notify_action_name(self) -> str | None:
        return NOTIFY_ACTION_MAPPINGS.get(self.id)

    @property
    def is_home(self) -> bool:
        return self.state == "home"

    def notify(self, notif: Notif) -> None:
        notif.send(self)
