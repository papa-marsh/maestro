from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import Domain


class DeviceTracker(Entity):
    domain = Domain.DEVICE_TRACKER
