from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import Domain


class Maestro(Entity):
    domain = Domain.MAESTRO
