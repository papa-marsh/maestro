from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import Domain


class BinarySensor(Entity):
    domain = Domain.BINARY_SENSOR
