"""Mock State Manager for testing that uses in-memory mocks."""

from typing import Any

from maestro.integrations.home_assistant.types import EntityData, EntityId
from maestro.utils.testing.mock_hass_client import MockHomeAssistantClient
from maestro.utils.testing.mock_redis import MockRedisClient


class MockStateManager:
    """
    Mock StateManager that uses MockHomeAssistantClient and MockRedisClient.

    This class mirrors the interface of the real StateManager but operates
    entirely in memory for fast, isolated unit tests.
    """

    def __init__(
        self,
        hass_client: MockHomeAssistantClient | None = None,
        redis_client: MockRedisClient | None = None,
    ) -> None:
        self.hass_client = hass_client or MockHomeAssistantClient()
        self.redis_client = redis_client or MockRedisClient()

    def get_cached_state(self, id: Any) -> Any:
        """Retrieve an entity's state or attribute value from Redis cache."""
        encoded_value = self.redis_client.get(key=id.cache_key)
        if encoded_value is None:
            return None

        import json

        from maestro.integrations.redis import CachedValue

        data = json.loads(encoded_value)
        cached_state = CachedValue(value=data["value"], type=data["type"])

        return self.redis_client.decode_cached_state(cached_state)

    def set_cached_state(self, id: Any, value: Any) -> Any:
        """Cache an entity's type-encoded state or attribute value."""
        import json

        from maestro.integrations.redis import CachedValue

        if id.is_entity and not isinstance(value, str):
            raise TypeError("State value must be a string")

        if id.is_attribute and isinstance(value, str):
            from contextlib import suppress

            from maestro.utils.dates import resolve_timestamp

            with suppress(ValueError):
                value = resolve_timestamp(value)

        encoded_value = self.redis_client.encode_cached_state(value)
        old_encoded_value = self.redis_client.set(key=id.cache_key, value=encoded_value)

        if old_encoded_value is None:
            return None

        old_data = json.loads(old_encoded_value)
        old_cached_state = CachedValue(value=old_data["value"], type=old_data["type"])

        return self.redis_client.decode_cached_state(old_cached_state)

    def upsert_hass_entity(
        self,
        entity_id: EntityId,
        state: str,
        attributes: dict[str, Any],
        create_only: bool = False,
    ) -> EntityData:
        """Create or update an entity in Home Assistant and cache it."""
        from contextlib import suppress

        with suppress(ValueError):
            if create_only and self.fetch_hass_entity(entity_id):
                raise FileExistsError(f"Entity {entity_id} already exists in Home Assistant")

        entity_data, _ = self.hass_client.set_entity(entity_id, state, attributes)
        self.cache_entity(entity_data)

        return entity_data

    def get_all_entity_keys(self, entity_id: EntityId) -> list[str]:
        """Returns a list of all cached state and attribute keys for a given entity ID."""
        from maestro.integrations.redis import CachePrefix

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
        """Overwrite an entity's state and attributes in cache."""
        from maestro.integrations.home_assistant.types import AttributeId
        from maestro.utils.logger import log

        keys_to_delete = set(self.get_all_entity_keys(entity_data.entity_id))
        keys_to_delete.discard(entity_data.entity_id.cache_key)

        self.set_cached_state(id=entity_data.entity_id, value=entity_data.state)

        for attribute, value in entity_data.attributes.items():
            try:
                attribute_id = AttributeId(f"{entity_data.entity_id}.{attribute}")
            except ValueError:
                log.warning(
                    "Attribute name failed validation while caching entity. Skipping.",
                    entity_id=entity_data.entity_id,
                    attribute_name=attribute,
                )
                continue

            self.set_cached_state(id=attribute_id, value=value)
            keys_to_delete.discard(attribute_id.cache_key)

        if keys_to_delete:
            self.redis_client.delete(*keys_to_delete)

    def delete_cached_entity(self, entity_id: EntityId) -> int:
        """Remove an entity and its attributes from the cache."""
        if keys_to_delete := self.get_all_entity_keys(entity_id):
            return self.redis_client.delete(*keys_to_delete)

        return 0

    def fetch_hass_entity(
        self,
        entity_id: EntityId,
        force_registry_update: bool = False,
    ) -> EntityData:
        """Fetch and cache up-to-date data for a Home Assistant entity."""
        entity_data = self.hass_client.get_entity(entity_id)
        if not entity_data:
            raise ValueError(f"Failed to retrieve an entity response for {entity_id}")

        self.cache_entity(entity_data)

        return entity_data

    def fetch_all_hass_entities(self, force_registry_update: bool = False) -> int:
        """Fetch and cache all hass entities."""
        all_entities = self.hass_client.get_all_entities()
        cached_count = 0

        for entity_data in all_entities:
            self.cache_entity(entity_data)
            cached_count += 1

        return cached_count
