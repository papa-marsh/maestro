from datetime import datetime

from maestro.domains.entity import Entity, EntityAttribute
from maestro.integrations.home_assistant.types import Domain


class Sun(Entity):
    domain = Domain.SUN

    next_dawn = EntityAttribute(datetime)
    next_dusk = EntityAttribute(datetime)
    next_midnight = EntityAttribute(datetime)
    next_noon = EntityAttribute(datetime)
    next_rising = EntityAttribute(datetime)
    next_setting = EntityAttribute(datetime)
    elevation = EntityAttribute(float)
    azimuth = EntityAttribute(float)
    rising = EntityAttribute(bool)
