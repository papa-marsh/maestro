import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from maestro.integrations.home_assistant.domain import Domain
from maestro.utils.dates import resolve_timestamp
from maestro.utils.exceptions import EntityMissingFromRegistryError, MalformedRegistryModule

if TYPE_CHECKING:
    from maestro.domains import Entity


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

    attribute: None

    def __new__(cls, value: str) -> "EntityId":
        if not re.match(cls.entity_pattern, value):
            raise ValueError(f"Invalid entity format: {value}")

        return str.__new__(cls, value)

    def resolve_entity(self) -> "Entity":
        """Resolve this EntityId to its actual registered Entity subclass instance."""
        import importlib

        from maestro.domains import Entity

        registry_module = importlib.import_module(f"maestro.registry.{self.domain}")
        entity = getattr(registry_module, self.entity, None)

        if entity is None:
            raise EntityMissingFromRegistryError(f"Couldn't find `{self}` in registry")

        if not isinstance(entity, Entity):
            raise MalformedRegistryModule(f"Registry returned non-entity object for {self}")

        return entity


class AttributeId(StateId):
    """A validated Home Assistant attribute ID (domain.entity.attribute)"""

    attribute: str

    def __new__(cls, value: str) -> "AttributeId":
        if not re.match(cls.attribute_pattern, value):
            raise ValueError(f"Invalid attribute format: {value}")

        return str.__new__(cls, value)

    def __init__(self, value: str):
        super().__init__(value)
        self.entity_id = EntityId(f"{self.domain}.{self.entity}")


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
class EventContext:
    id: str
    parent_id: str | None
    user_id: str | None


@dataclass
class WebSocketEvent:
    """Raw WebSocket event from Home Assistant event bus"""

    event_type: str
    data: dict[str, Any]
    time_fired: datetime
    origin: str
    context: EventContext


@dataclass
class FiredEvent:
    """Generic data payload for incoming websocket events"""

    time_fired: datetime
    type: str
    data: dict
    user_id: str | None


@dataclass
class StateChangeEvent(FiredEvent):
    """Specific event payload type for state changes"""

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
