import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from maestro.integrations.home_assistant.domain import Domain
from maestro.utils.dates import resolve_timestamp


class StateId(str):
    """A validated Home Assistant entity or attribute ID"""

    entity_pattern = r"^[a-z_][a-z0-9_]*\.[a-z0-9_]+$"
    attribute_pattern = r"^[a-z_][a-z0-9_]*\.[a-z0-9_]+\.[a-z0-9_]+$"

    def __new__(cls, value: str) -> "StateId":
        if not (re.match(cls.entity_pattern, value) or re.match(cls.attribute_pattern, value)):
            raise ValueError(f"Invalid entity or attribute format: {value}")

        return str.__new__(cls, value)

    def __init__(self, _: str):
        from maestro.integrations.redis import CachePrefix, RedisClient

        super().__init__()
        parts = self.split(".")

        self.domain = Domain(parts[0])
        self.entity = parts[1]
        self.attribute = parts[2] if len(parts) > 2 else None

        self.is_entity = self.attribute is None
        self.is_attribute = self.attribute is not None

        self.domain_class_name = "".join(word.capitalize() for word in self.domain.split("_"))
        self.cache_key = RedisClient.build_key(CachePrefix.STATE, *parts)


class EntityId(StateId):
    """A validated Home Assistant entity ID (domain.entity)"""

    def __new__(cls, value: str) -> "EntityId":
        if not re.match(cls.entity_pattern, value):
            raise ValueError(f"Invalid entity format: {value}")

        return str.__new__(cls, value)

    def resolve_entity(self) -> Any:
        """Resolve this EntityId to its actual registered Entity subclass instance."""
        import importlib

        registry_module = importlib.import_module(f"maestro.registry.{self.domain}")
        return getattr(registry_module, self.entity)


class AttributeId(StateId):
    """A validated Home Assistant attribute ID (domain.entity.attribute)"""

    def __new__(cls, value: str) -> "AttributeId":
        if not re.match(cls.attribute_pattern, value):
            raise ValueError(f"Invalid attribute format: {value}")

        return str.__new__(cls, value)


@dataclass
class EntityData:
    """An entity's (sanitized) state and metadata as represented by the Home Assistant API"""

    entity_id: EntityId
    state: str
    attributes: dict[str, Any]

    def __post_init__(self) -> None:
        """
        Sanitize attribute name to handle spaces/uppercase chars.
        Resolve timestamps strings into datetime objects.
        """
        sanitized_attributes = {}
        for key, value in self.attributes.items():
            if isinstance(value, str):
                with suppress(ValueError):
                    value = resolve_timestamp(value)
            new_key = key.replace(" ", "_").lower()
            sanitized_attributes[new_key] = value

        self.attributes = sanitized_attributes


@dataclass
class FiredEvent:
    """Generic event data payload for incoming webhooks"""

    timestamp: datetime
    time_fired: datetime
    type: str
    data: dict
    user_id: str | None


@dataclass
class StateChangeEvent:
    """Specific event payload type for state changes"""

    timestamp: datetime
    time_fired: datetime
    entity_id: EntityId
    old: EntityData
    new: EntityData


@dataclass
class NotifActionEvent(FiredEvent):
    """Specific event payload type for iOS notification actions"""

    name: str
    action_data: Any
    device_id: str
    device_name: str
