from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class DeviceTracker(Entity):
    domain = Domain.DEVICE_TRACKER
    allow_set_state = False
