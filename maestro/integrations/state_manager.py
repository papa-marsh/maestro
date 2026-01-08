import json
from contextlib import suppress
from typing import Any

from maestro.config import AUTOPOPULATE_REGISTRY
from maestro.integrations.home_assistant.client import HomeAssistantClient
from maestro.integrations.home_assistant.types import AttributeId, EntityData, EntityId, StateId
from maestro.integrations.redis import CachedValue, CachedValueT, CachePrefix, RedisClient
from maestro.registry.registry_manager import RegistryManager
from maestro.utils.dates import IntervalSeconds, local_now, resolve_timestamp
from maestro.utils.exceptions import (
    AttributeDoesNotExistError,
    EntityAlreadyExistsError,
    EntityDoesNotExistError,
)
from maestro.utils.internal import test_mode_active
from maestro.utils.logging import log


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

        if test_mode_active():
            self._initialize_as_mock()

    def _initialize_as_mock(self) -> None:
        """Override clients with existing mock clients if they exist"""
        from maestro.testing.context import get_test_state_manager
        from maestro.testing.mocks import MockHomeAssistantClient, MockRedisClient

        if isinstance(self.hass_client, MockHomeAssistantClient) and isinstance(
            self.redis_client, MockRedisClient
        ):
            return

        test_state_manager = get_test_state_manager()
        self.hass_client = test_state_manager.hass_client
        self.redis_client = test_state_manager.redis_client

    def get_entity_state(self, entity_id: EntityId) -> str:
        """Retrieve an entity's cached state or fetch from HASS on cache miss"""
        state = self.get_cached_state(entity_id)

        if state is None:
            entity_data = self.fetch_hass_entity(entity_id)
            state = entity_data.state

        if not isinstance(state, str):
            raise TypeError(f"Cached state for {entity_id} is {type(state).__name__}, not string")

        return state

    def get_attribute_state(
        self,
        attribute_id: AttributeId,
        expected_type: type[CachedValueT],
    ) -> CachedValueT:
        """Retrieve an attribute's cached state or fetch from HASS on cache miss"""
        attribute_state = self.get_cached_state(attribute_id)

        if attribute_state is None:
            entity_data = self.fetch_hass_entity(entity_id=attribute_id.entity_id)
            attribute_state = entity_data.attributes.get(attribute_id.attribute)

        if attribute_state is None:
            raise AttributeDoesNotExistError(f"Attribute {attribute_id} not found")

        if not isinstance(attribute_state, expected_type):
            raise TypeError(
                f"Type mismatch for attribute {attribute_id}. "
                f"Expected {expected_type.__name__} but got {type(attribute_state).__name__}"
            )

        return attribute_state

    def get_cached_state(self, id: StateId) -> CachedValueT | None:
        """Retrieve an entity's state or attribute value from Redis"""
        encoded_value = self.redis_client.get(key=id.cache_key)
        if encoded_value is None:
            return None

        data = json.loads(encoded_value)
        cached_state = CachedValue(value=data["value"], type=data["type"])

        return self.redis_client.decode_cached_state(cached_state)

    def set_cached_state(self, id: StateId, value: CachedValueT) -> CachedValueT | None:
        """Caches an entity's type-encoded state or attribute value. Returns the previous value"""
        if id.is_entity and not isinstance(value, str):
            raise TypeError("State value must be a string")

        if id.is_attribute and isinstance(value, str):
            with suppress(ValueError):
                value = resolve_timestamp(value)

        encoded_value = self.redis_client.encode_cached_state(value)
        old_encoded_value = self.redis_client.set(
            key=id.cache_key,
            value=encoded_value,
            ttl_seconds=IntervalSeconds.ONE_WEEK,
        )

        if old_encoded_value is None:
            return None

        old_data = json.loads(old_encoded_value)
        old_cached_state = CachedValue(value=old_data["value"], type=old_data["type"])

        return self.redis_client.decode_cached_state(old_cached_state)

    def set_hass_state(self, id: StateId, value: Any) -> EntityData:
        """Update a single state or attribute in Home Assistant and cache locally to Redis"""
        if isinstance(id, AttributeId):
            entity_id = id.entity_id
            attribute_name = id.attribute
        else:
            entity_id = EntityId(id)

        entity_data = self.fetch_hass_entity(entity_id)

        if id.is_entity:
            if not isinstance(value, str):
                raise TypeError("Entity state must be string")
            entity_data.state = value
        elif not value:
            entity_data.attributes.pop(attribute_name, None)
        else:
            entity_data.attributes[attribute_name] = value

        return self.set_hass_entity(
            entity_id=entity_id,
            state=entity_data.state,
            attributes=entity_data.attributes,
        )

    def set_hass_entity(
        self,
        entity_id: EntityId,
        state: str,
        attributes: dict[str, Any],
        create_only: bool = False,
    ) -> EntityData:
        """Create or update an entity in Home Assistant and cache locally to Redis"""
        with suppress(EntityDoesNotExistError):
            if create_only and self.fetch_hass_entity(entity_id):
                raise EntityAlreadyExistsError(f"Entity {entity_id} already exists in HASS")

        entity_data, _ = self.hass_client.set_entity(entity_id, state, attributes)
        self.cache_entity(entity_data)

        return entity_data

    def initialize_hass_entity(
        self,
        entity_id: EntityId,
        state: str,
        attributes: dict[str, Any],
        restore_cached: bool = False,
    ) -> tuple[EntityData, bool]:
        """
        Create and cache a home assistant entity only if it doesn't already exist.
        Returns the EntityData and a `created` boolean.

        Optionally restore the entity from cache if it exists. Useful for custom
        entities that aren't persisted across Home Assistant restarts. Restoring from
        cache will prioritize cached data over any values passed as arguments.
        """
        with suppress(EntityDoesNotExistError):
            entity_data = self.fetch_hass_entity(entity_id)
            return entity_data, False

        if restore_cached and (cached_entity := self.fetch_cached_entity(entity_id)):
            log.info(
                "Restoring initialized entity from cache",
                entity_id=entity_id,
                cached_state=cached_entity.state,
                cached_attributes=cached_entity.attributes,
            )
            state = cached_entity.state
            for cached_attribute, value in cached_entity.attributes.items():
                attributes[cached_attribute] = value

        entity_data = self.set_hass_entity(entity_id, state, attributes, create_only=True)
        created = True

        return entity_data, created

    def get_all_entity_keys(self, entity_id: EntityId) -> list[str]:
        """Returns a list of all cached state and attribute keys for a given entity ID"""
        attribute_pattern = self.redis_client.build_key(
            CachePrefix.STATE,
            entity_id.domain,
            entity_id.entity,
            "*",
        )

        keys = [entity_id.cache_key]
        keys.extend(self.redis_client.get_keys(pattern=attribute_pattern))

        return keys

    def cache_entity(self, entity_data: EntityData) -> None:
        """Overwrite an entity's state and attributes, removing any stale attributes"""

        keys_to_delete = set(self.get_all_entity_keys(entity_data.entity_id))
        keys_to_delete.remove(entity_data.entity_id.cache_key)

        self.set_cached_state(id=entity_data.entity_id, value=entity_data.state)

        for attribute, value in entity_data.attributes.items():
            if value is None:
                log.info(
                    "Cache skipped for attribute with value of None",
                    entity_id=entity_data.entity_id,
                    attribute=attribute,
                )
                continue

            try:
                attribute_id = AttributeId(f"{entity_data.entity_id}.{attribute}")
            except ValueError:
                log.info(
                    "Attribute name failed validation while caching entity. Skipping attribute.",
                    entity_id=entity_data.entity_id,
                    attribute_name=attribute,
                )
                continue

            self.set_cached_state(id=attribute_id, value=value)
            keys_to_delete.discard(attribute_id.cache_key)

        if keys_to_delete:
            self.redis_client.delete(*keys_to_delete)

        if AUTOPOPULATE_REGISTRY and not test_mode_active():
            RegistryManager.upsert_entity(entity_data)

    def fetch_cached_entity(self, entity_id: EntityId) -> EntityData | None:
        attributes = {}
        if not (state := self.get_cached_state(entity_id)):
            return None
        if not isinstance(state, str):
            raise TypeError

        for key in self.get_all_entity_keys(entity_id):
            parts = key.split(":")
            if len(parts) == 3:
                continue

            attribute_id = AttributeId(".".join(parts[1:]))
            attributes[attribute_id.attribute] = self.get_cached_state(attribute_id)

        return EntityData(entity_id=entity_id, state=state, attributes=attributes)

    def delete_cached_entity(self, entity_id: EntityId) -> int:
        """Remove an entity and its attributes from the cache. Returns the count deleted."""
        if keys_to_delete := self.get_all_entity_keys(entity_id):
            return self.redis_client.delete(*keys_to_delete)

        return 0

    def fetch_hass_entity(
        self,
        entity_id: EntityId,
        force_registry_update: bool = False,
    ) -> EntityData:
        """Fetch and cache up-to-date data for a Home Assistant entity"""
        entity_data = self.hass_client.get_entity(entity_id)

        if force_registry_update:
            cache_key = RedisClient.build_key(CachePrefix.REGISTERED, entity_id)
            self.redis_client.delete(cache_key)

        self.cache_entity(entity_data)

        return entity_data

    def fetch_all_hass_entities(self, force_registry_update: bool = False) -> int:
        """Fetch and cache all hass entities, respecting the domain ignore list."""
        start_time = local_now()
        all_entities = self.hass_client.get_all_entities()
        cached_count = 0

        if force_registry_update:
            keys_to_delete = self.redis_client.get_keys(pattern=f"{CachePrefix.REGISTERED}*")
            self.redis_client.delete(*keys_to_delete)

        for entity_data in all_entities:
            self.cache_entity(entity_data)
            cached_count += 1

        log.info(
            "Fetched and cached all Home Assistant entities",
            duration_seconds=(local_now() - start_time).total_seconds(),
            entity_count=cached_count,
        )

        return cached_count
