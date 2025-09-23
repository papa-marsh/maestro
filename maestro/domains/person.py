from maestro.domains.entity import Entity, EntityAttribute
from maestro.integrations.home_assistant.types import Domain


class Person(Entity):
    domain = Domain.PERSON

    device_trackers = EntityAttribute(list)
    latitude = EntityAttribute(float)
    longitude = EntityAttribute(float)
    gps_accuracy = EntityAttribute(int)
    source = EntityAttribute(str)
    user_id = EntityAttribute(str)
    entity_picture = EntityAttribute(str)
