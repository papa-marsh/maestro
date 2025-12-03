import re
from http import HTTPStatus
from typing import Any, override

from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.client import HomeAssistantClient
from maestro.integrations.home_assistant.domain import Domain
from maestro.integrations.home_assistant.types import EntityData, EntityId
from maestro.integrations.redis import RedisClient
from maestro.utils.dates import local_now
from maestro.utils.exceptions import TestImplementationError


class ActionCall:
    """Represents a single action call made during testing"""

    def __init__(
        self,
        domain: Domain,
        action: str,
        entity_id: str | list[str] | None = None,
        **kwargs: Any,
    ):
        self.domain = domain
        self.action = action
        self.entity_id = entity_id
        self.kwargs = kwargs
        self.timestamp = local_now()

    def __repr__(self) -> str:
        entity_str = f", entity_id={self.entity_id}" if self.entity_id else ""
        kwargs_str = f", {self.kwargs}" if self.kwargs else ""
        return f"ActionCall({self.domain}.{self.action}{entity_str}{kwargs_str})"


class MockHomeAssistantClient(HomeAssistantClient):
    """
    Mock Home Assistant client that simulates API calls without hitting a real instance.
    Maintains in-memory state for entities and tracks all action calls.
    """

    def __init__(self) -> None:
        self._entities: dict[str, EntityData] = {}
        self._action_calls: list[ActionCall] = []
        self._healthy = True

    def reset(self) -> None:
        """Reset mock HASS client and clear stored entities & action calls."""
        self._entities.clear()
        self._action_calls.clear()
        self._healthy = True

    def set_health(self, healthy: bool) -> None:
        """Manually set mock client health"""
        self._healthy = healthy

    def get_action_calls(
        self,
        domain: Domain | None = None,
        action: str | None = None,
        entity: Entity | str | None = None,
    ) -> list[ActionCall]:
        """Get all action calls, optionally filtered by domain, action, or entity_id."""
        filtered = self._action_calls

        if domain is not None:
            filtered = [call for call in filtered if call.domain == domain]

        if action is not None:
            filtered = [call for call in filtered if call.action == action]

        if entity is not None:
            entity_id = entity.id if isinstance(entity, Entity) else EntityId(entity)
            filtered = [
                call
                for call in filtered
                if call.entity_id == entity_id
                or (isinstance(call.entity_id, list) and entity_id in call.entity_id)
            ]

        return filtered

    def clear_action_calls(self) -> None:
        """Remove all stored mock action calls"""
        self._action_calls.clear()

    @override
    def check_health(self) -> bool:
        """Always returns True unless set manually to False"""
        return self._healthy

    @override
    def get_entity(self, entity_id: str) -> EntityData:
        """Get a mock entity by ID"""
        if entity_id not in self._entities:
            raise TestImplementationError(f"Entity {entity_id} doesn't exist")
        return self._entities[entity_id]

    @override
    def get_all_entities(self) -> list[EntityData]:
        """Get all mock entities"""
        return list(self._entities.values())

    @override
    def set_entity(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any],
    ) -> tuple[EntityData, bool]:
        """Create or update a mock entity"""
        entity_id = EntityId(entity_id)
        created = entity_id not in self._entities

        now = local_now()
        attributes["last_changed"] = now
        attributes["last_reported"] = now
        attributes["last_updated"] = now

        if "friendly_name" not in attributes:
            attributes["friendly_name"] = entity_id.entity.replace("_", " ").title()

        entity_data = EntityData(
            entity_id=entity_id,
            state=state,
            attributes=attributes,
        )

        self._entities[entity_id] = entity_data
        return entity_data, created

    @override
    def delete_entity(self, entity_id: str) -> None:
        """Delete a mock entity"""
        if entity_id not in self._entities:
            raise TestImplementationError(f"Entity {entity_id} doesn't exist")
        del self._entities[entity_id]

    @override
    def perform_action(
        self,
        domain: Domain,
        action: str,
        entity_id: str | list[str] | None = None,
        **body_params: Any,
    ) -> list[EntityData]:
        """Record an action call and return mock entity states"""
        action_call = ActionCall(domain, action, entity_id, **body_params)
        self._action_calls.append(action_call)

        if entity_id is None:
            return []

        entity_ids = (
            [EntityId(id) for id in entity_id]
            if isinstance(entity_id, list)
            else [EntityId(entity_id)]
        )

        entities = [self._entities[id] for id in entity_ids if id in self._entities]

        return entities

    @override
    def execute_request(
        self,
        _method: Any,
        _path: str,
        _body: dict | None = None,
    ) -> tuple[dict | list, int]:
        """Mock HTTP request execution - not typically used directly in tests"""
        return {}, HTTPStatus.OK


class MockRedisClient(RedisClient):
    """
    Mock Redis client that uses in-memory dict instead of actual Redis.
    Implements all RedisClient methods for testing without external dependencies.
    """

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}
        self._healthy = True

    def reset(self) -> None:
        """Clear all cached data"""
        self._cache.clear()
        self._healthy = True

    def set_health(self, healthy: bool) -> None:
        """Manually set mock client health"""
        self._healthy = healthy

    @override
    def check_health(self) -> bool:
        """Always returns True unless set manually to False"""
        return self._healthy

    @override
    def get(self, key: str) -> str | None:
        """Get a string value by key"""
        return self._cache.get(key)

    @override
    def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> str | None:
        """Set a string value (ttl_seconds ignored in mock)"""
        old_value = self._cache.get(key)
        self._cache[key] = value
        return old_value

    @override
    def delete(self, *keys: str) -> int:
        """Delete one or more keys. Returns number of keys deleted"""
        count = 0
        for key in keys:
            if key in self._cache:
                del self._cache[key]
                count += 1
        return count

    @override
    def exists(self, *keys: str) -> int:
        """Check if keys exist. Returns count of existing keys"""
        return sum(1 for key in keys if key in self._cache)

    @override
    def get_keys(self, pattern: str | None = None) -> list[str]:
        """Returns a list of keys, optionally filtered by pattern"""
        if pattern is None:
            return list(self._cache.keys())

        regex_pattern = pattern.replace("*", ".*")
        regex = re.compile(f"^{regex_pattern}$")
        return [key for key in self._cache if regex.match(key)]
