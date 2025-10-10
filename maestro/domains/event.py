from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Event(Entity):
    domain = Domain.EVENT
