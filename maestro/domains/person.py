from maestro.config import NOTIFY_ACTION_MAPPINGS
from maestro.domains.entity import HOME, Entity
from maestro.integrations.home_assistant.domain import Domain
from maestro.utils.internal import test_mode_active
from maestro.utils.push import Notif


class Person(Entity):
    domain = Domain.PERSON

    @property
    def notify_action_name(self) -> str:
        if test_mode_active():
            return f"test_mock_notify_{self.id.entity}"

        return NOTIFY_ACTION_MAPPINGS.get(self.id, "")

    @property
    def is_home(self) -> bool:
        return self.state == HOME

    def notify(self, notif: Notif) -> None:
        notif.send(self)
