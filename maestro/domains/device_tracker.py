from maestro.domains.entity import HOME, Entity
from maestro.integrations.home_assistant.domain import Domain


class DeviceTracker(Entity):
    domain = Domain.DEVICE_TRACKER
    allow_set_state = False

    @property
    def is_home(self) -> bool:
        return self.state == HOME
