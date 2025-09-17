from structlog.stdlib import get_logger

from maestro.domains import Entity
from maestro.domains.entity import EntityAttribute

log = get_logger()


def validate_attributes(entity: Entity) -> None:
    for d in dir(entity):
        attribute = getattr(entity, d)
        if not isinstance(attribute, EntityAttribute):
            continue
        log.info(f"{attribute.name}: {attribute}")
