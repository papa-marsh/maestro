from maestro.domains.entity import Entity, EntityAttribute
from maestro.integrations.home_assistant.types import Domain


class DeviceTracker(Entity):
    domain = Domain.DEVICE_TRACKER