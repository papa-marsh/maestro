from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import Domain


class Sensor(Entity):
    domain = Domain.SENSOR
