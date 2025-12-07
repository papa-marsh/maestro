from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Sun(Entity):
    domain = Domain.SUN
    allow_set_state = False
