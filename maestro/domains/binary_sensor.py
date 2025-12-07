from maestro.domains.entity import ON, Entity
from maestro.integrations.home_assistant.domain import Domain


class BinarySensor(Entity):
    domain = Domain.BINARY_SENSOR
    allow_set_state = False

    @property
    def is_on(self) -> bool:
        return self.state == ON
