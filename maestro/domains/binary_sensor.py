from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class BinarySensor(Entity):
    domain = Domain.BINARY_SENSOR
