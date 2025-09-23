from maestro.domains.entity import Entity, EntityAttribute
from maestro.integrations.home_assistant.types import Domain


class Zone(Entity):
    domain = Domain.ZONE

    latitude = EntityAttribute(float)
    longitude = EntityAttribute(float)
    radius = EntityAttribute(float)
    passive = EntityAttribute(bool)
    persons = EntityAttribute(list)
