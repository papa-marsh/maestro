from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import Domain


class Person(Entity):
    domain = Domain.PERSON
