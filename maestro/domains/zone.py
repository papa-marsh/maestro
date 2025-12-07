from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Zone(Entity):
    domain = Domain.ZONE
    allow_set_state = False
