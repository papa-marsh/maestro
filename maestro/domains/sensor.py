from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Sensor(Entity):
    domain = Domain.SENSOR
