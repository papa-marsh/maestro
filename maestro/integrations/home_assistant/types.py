import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, auto
from typing import Any


class Domain(StrEnum):
    BINARY_SENSOR = auto()
    BUTTON = auto()
    CALENDAR = auto()
    CLIMATE = auto()
    COVER = auto()
    DEVICE_TRACKER = auto()
    EVENT = auto()
    FAN = auto()
    HOME_ASSISTANT = auto()
    HUMIDIFIER = auto()
    INPUT_BOOLEAN = auto()
    INPUT_NUMBER = auto()
    INPUT_SELECT = auto()
    INPUT_TEXT = auto()
    LIGHT = auto()
    LOCK = auto()
    MAESTRO = auto()
    MEDIA_PLAYER = auto()
    NUMBER = auto()
    PERSON = auto()
    REMOTE = auto()
    SELECT = auto()
    SENSOR = auto()
    SONOS = auto()
    SUN = auto()
    SWITCH = auto()
    UPDATE = auto()
    WEATHER = auto()
    ZONE = auto()


class StateId(str):
    """A validated Home Assistant entity or attribute ID"""

    entity_pattern = r"^[a-z_][a-z0-9_]*\.[a-z0-9_]+$"
    attribute_pattern = r"^[a-z_][a-z0-9_]*\.[a-z0-9_]+\.[a-z0-9_]+$"

    def __new__(cls, value: str) -> "StateId":
        if not (re.match(cls.entity_pattern, value) or re.match(cls.attribute_pattern, value)):
            raise ValueError(f"Invalid entity or attribute format: {value}")

        return str.__new__(cls, value)

    def __init__(self, _: str):
        from maestro.integrations.redis import RedisClient
        from maestro.integrations.state_manager import STATE_CACHE_PREFIX

        super().__init__()
        parts = self.split(".")

        self.domain = Domain(parts[0])
        self.entity = parts[1]
        self.attribute = parts[2] if len(parts) > 2 else None

        self.is_entity = self.attribute is None
        self.is_attribute = self.attribute is not None

        self.domain_class_name = "".join(word.capitalize() for word in self.domain.split("_"))
        self.cache_key = RedisClient.build_key(STATE_CACHE_PREFIX, *parts)


class EntityId(StateId):
    """A validated Home Assistant entity ID (domain.entity)"""

    def __new__(cls, value: str) -> "EntityId":
        if not re.match(cls.entity_pattern, value):
            raise ValueError(f"Invalid entity format: {value}")

        return str.__new__(cls, value)


class AttributeId(StateId):
    """A validated Home Assistant attribute ID (domain.entity.attribute)"""

    def __new__(cls, value: str) -> "AttributeId":
        if not re.match(cls.attribute_pattern, value):
            raise ValueError(f"Invalid attribute format: {value}")

        return str.__new__(cls, value)


@dataclass
class EntityData:
    """An entity's state and metadata as represented by the Home Assistant API"""

    entity_id: EntityId
    state: str
    attributes: dict[str, Any]

    def __post_init__(self) -> None:
        self.attributes = sanitize_attribute_keys(self.attributes)


@dataclass
class StateChangeEvent:
    """A state change event as represented by the maestro_send_state_changed automation"""

    timestamp: datetime
    time_fired: datetime
    entity_id: EntityId
    old: EntityData
    new: EntityData


def sanitize_attribute_keys(attributes: dict[str, Any]) -> dict[str, Any]:
    """
    Temporary (maybe) shim logic to handle spaces and uppercase chars in attribute names.
    Otherwise, it breaks the EntityAttribute class, which relies on its own property name.
    Theoretically, this should only present a problem if we try to set a value for an attribute with
    uppercase/spaces. But overwriting existing HASS attributes doesn't seem like a
    realistic use case; nor should we ever be creating new attributes with uppercase/spaces.
    """
    sanitized = {}
    for key in attributes:
        new_key = key.replace(" ", "_").lower()
        sanitized[new_key] = attributes[key]

    return sanitized


@dataclass
class FiredEvent:
    """Event data payload as captured by the maestro_event_fired_url automation"""

    timestamp: datetime
    time_fired: datetime
    type: str
    data: dict
    user_id: EntityId | str | None
