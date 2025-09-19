import contextlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from structlog.stdlib import get_logger

from maestro.config import AUTOPOPULATE_REGISTRY
from maestro.integrations.home_assistant.client import (
    HomeAssistantClient,
)
from maestro.integrations.home_assistant.types import (
    AttributeId,
    EntityData,
    EntityId,
    StateId,
)
from maestro.integrations.redis import RedisClient
from maestro.utils.dates import resolve_timestamp
from maestro.utils.infra import add_entity_to_registry

STATE_CACHE_PREFIX = "STATE"


@dataclass
class CachedState:
    value: str
    type: str


CachedStateValueT = str | int | float | dict | list | bool | datetime | None

state_encoder_map: dict[str, Callable[[CachedStateValueT], str]] = {
    str.__name__: lambda x: str(x),
    int.__name__: lambda x: str(x),
    float.__name__: lambda x: str(x),
    dict.__name__: lambda x: json.dumps(x),
    list.__name__: lambda x: json.dumps(x),
    bool.__name__: lambda x: str(x),
    datetime.__name__: lambda x: x.isoformat() if isinstance(x, datetime) else "",
    type(None).__name__: lambda _: "",
}
state_decoder_map: dict[str, Callable[[str], CachedStateValueT]] = {
    str.__name__: lambda x: str(x),
    int.__name__: lambda x: int(x),
    float.__name__: lambda x: float(x),
    dict.__name__: lambda x: json.loads(x) if isinstance(x, str) else dict(x),
    list.__name__: lambda x: json.loads(x) if isinstance(x, str) else list(x),
    bool.__name__: lambda x: x.lower() == "true",
    datetime.__name__: lambda x: resolve_timestamp(x),
    type(None).__name__: lambda _: None,
}

log = get_logger()


class StateManager:
    """
    Middleware that sits between Home Assistant and the main logic engine.
    Orchestrates entity data handoffs to & from HASS and the cache layer.
    """

    hass_client: HomeAssistantClient
    redis_client: RedisClient

    def __init__(
        self,
        hass_client: HomeAssistantClient | None = None,
        redis_client: RedisClient | None = None,
    ) -> None:
        self.hass_client = hass_client or HomeAssistantClient()
        self.redis_client = redis_client or RedisClient()

    def get_cached_state(self, id: StateId) -> CachedStateValueT:
        """Retrieve an entity's state or attribute value from Redis"""
        encoded_value = self.redis_client.get(key=id.cache_key)
        if encoded_value is None:
            return None

        data = json.loads(encoded_value)
        cached_state = CachedState(value=data["value"], type=data["type"])

        return self.decode_cached_state(cached_state)

    def set_cached_state(self, id: StateId, value: CachedStateValueT) -> CachedStateValueT:
        """Caches an entity's type-encoded state or attribute value. Returns the previous value"""
        if id.is_entity and not isinstance(value, str):
            raise TypeError("State value must be a string")

        if id.is_attribute and isinstance(value, str):
            with contextlib.suppress(ValueError):
                value = resolve_timestamp(value)

        encoded_value = self.encode_cached_state(value)
        old_encoded_value = self.redis_client.set(key=id.cache_key, value=encoded_value)

        if old_encoded_value is None:
            if id.is_entity and AUTOPOPULATE_REGISTRY:
                add_entity_to_registry(EntityId(id))
            return None

        old_data = json.loads(old_encoded_value)
        old_cached_state = CachedState(value=old_data["value"], type=old_data["type"])

        return self.decode_cached_state(old_cached_state)

    def get_all_entity_keys(self, entity_id: EntityId) -> list[str]:
        """Returns a list of all cached state and attribute keys for a given entity ID"""
        attribute_pattern = self.redis_client.build_key(
            STATE_CACHE_PREFIX,
            entity_id.domain,
            entity_id.entity,
            "*",
        )

        keys = [entity_id.cache_key]
        keys.extend(self.redis_client.get_keys(pattern=attribute_pattern))

        return keys

    @classmethod
    def encode_cached_state(cls, value: CachedStateValueT) -> str:
        type_name = type(value).__name__
        if type_name not in state_encoder_map:
            raise TypeError(f"No state encoder exists for type {type_name}")

        encoded_state = CachedState(
            value=state_encoder_map[type_name](value),
            type=type_name,
        )

        return json.dumps(
            {
                "value": encoded_state.value,
                "type": encoded_state.type,
            }
        )

    @classmethod
    def decode_cached_state(cls, cached_state: CachedState) -> CachedStateValueT:
        if cached_state.type not in state_decoder_map:
            raise TypeError(f"No state decoder exists for type {cached_state.type}")

        decoder_function = state_decoder_map[cached_state.type]

        return decoder_function(cached_state.value)

    def fetch_hass_entity(self, entity_id: EntityId) -> EntityData:
        """Fetch and cache up-to-date data for a Home Assistant entity"""
        entity_data = self.hass_client.get_entity(entity_id)
        if not entity_data:
            raise ValueError(f"Failed to retrieve an entity response for {entity_id}")
        self.cache_entity(entity_data)

        return entity_data

    def cache_entity(self, entity_data: EntityData) -> None:
        """Overwrite an entity's state and attributes, removing any stale attributes"""
        keys_to_delete = set(self.get_all_entity_keys(entity_data.entity_id))
        keys_to_delete.remove(entity_data.entity_id.cache_key)

        self.set_cached_state(id=entity_data.entity_id, value=entity_data.state)

        for attribute, value in entity_data.attributes.items():
            try:
                attribute_id = AttributeId(f"{entity_data.entity_id}.{attribute}")
            except ValueError:
                log.warning(
                    "Attribute name failed validation while caching entity. Skipping attribute.",
                    entity_id=entity_data.entity_id,
                    attribute_name=attribute,
                )
                continue

            self.set_cached_state(id=attribute_id, value=value)
            keys_to_delete.discard(attribute_id.cache_key)

        if keys_to_delete:
            self.redis_client.delete(*keys_to_delete)

    def delete_cached_entity(self, entity_id: EntityId) -> int:
        """Remove an entity and its attributes from the cache. Returns the count deleted."""
        if keys_to_delete := self.get_all_entity_keys(entity_id):
            return self.redis_client.delete(*keys_to_delete)

        return 0
