import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, auto
from typing import Any


class Domain(StrEnum):
    BINARY_SENSOR = auto()
    CALENDAR = auto()
    CLIMATE = auto()
    COVER = auto()
    DEVICE_TRACKER = auto()
    ENTITY = auto()  # For test cases
    EVENT = auto()
    FAN = auto()
    HUMIDIFIER = auto()
    INPUT_BOOLEAN = auto()
    LIGHT = auto()
    LOCK = auto()
    MAESTRO = auto()
    MEDIA_PLAYER = auto()
    NUMBER = auto()
    PERSON = auto()
    PYSCRIPT = auto()  # TODO: Remove once pyscript is gone
    SENSOR = auto()
    SUN = auto()
    SWITCH = auto()
    UPDATE = auto()
    WEATHER = auto()


class StateId(str):
    """A validated Home Assistant entity or attribute ID"""

    def __new__(cls, value: str) -> "StateId":
        entity_pattern = r"^[a-z_][a-z0-9_]*\.[a-z0-9_]+$"
        attribute_pattern = r"^[a-z_][a-z0-9_]*\.[a-z0-9_]+\.[a-z0-9_]+$"

        if not (re.match(entity_pattern, value) or re.match(attribute_pattern, value)):
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
        self.cache_key = RedisClient.build_key(STATE_CACHE_PREFIX, *parts)


class EntityId(StateId):
    """A validated Home Assistant entity ID (domain.entity)"""

    def __new__(cls, value: str) -> "EntityId":
        entity_pattern = r"^[a-z_][a-z0-9_]*\.[a-z0-9_]+$"

        if not re.match(entity_pattern, value):
            raise ValueError(f"Invalid entity format: {value}")

        return str.__new__(cls, value)


class AttributeId(StateId):
    """A validated Home Assistant attribute ID (domain.entity.attribute)"""

    def __new__(cls, value: str) -> "AttributeId":
        attribute_pattern = r"^[a-z_][a-z0-9_]*\.[a-z0-9_]+\.[a-z0-9_]+$"

        if not re.match(attribute_pattern, value):
            raise ValueError(f"Invalid attribute format: {value}")

        return str.__new__(cls, value)


@dataclass
class EntityResponse:
    """An entity's state and metadata as represented by the Home Assistant API"""

    entity_id: EntityId
    state: str
    attributes: dict[str, Any]
    last_changed: datetime
    last_reported: datetime
    last_updated: datetime


@dataclass
class StateChangeEvent:
    """A state change event as represented by the send_to_maestro automation"""

    timestamp: datetime
    time_fired: datetime
    event_type: str
    entity_id: EntityId
    old_state: str | None
    new_state: str | None
    old_attributes: dict[str, Any]
    new_attributes: dict[str, Any]
