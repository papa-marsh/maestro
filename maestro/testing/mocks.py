import hashlib
import re
from collections import deque
from collections.abc import Callable
from contextlib import nullcontext
from datetime import datetime, timedelta
from http import HTTPMethod, HTTPStatus
from typing import Any, override

from apscheduler.jobstores.base import JobLookupError  # type:ignore[import-untyped]
from redis.lock import Lock

from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.client import HomeAssistantClient
from maestro.integrations.home_assistant.domain import Domain
from maestro.integrations.home_assistant.types import EntityData, EntityId
from maestro.integrations.redis import CachedValueT, RedisClient
from maestro.utils.dates import local_now
from maestro.utils.exceptions import MockEntityDoesNotExistError


def hash_string(seed: str) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)


# Generates default values for mock attributes in test mode
mock_attribute_default_value_map: dict[type, Callable[[str], CachedValueT]] = {
    str: lambda name: f"test_{name}",
    int: lambda name: hash_string(name),
    float: lambda name: float(hash_string(name)),
    dict: lambda name: {"mock_value": name},
    list: lambda name: [name],
    bool: lambda _name: False,
    datetime: lambda name: datetime.fromtimestamp(0) + timedelta(seconds=hash_string(name)),
}


class ActionCall:
    """Represents a single action call made during testing"""

    def __init__(
        self,
        domain: Domain,
        action: str,
        response: dict[str, Any] | None,
        entity_id: str | list[str] | None = None,
        **kwargs: Any,
    ):
        self.domain = domain
        self.action = action
        self.response = response
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
        self._action_response_queue: deque[dict[str, Any]] = deque()
        self._healthy = True

    def reset(self) -> None:
        """Reset mock HASS client and clear stored entities & action calls."""
        self._entities.clear()
        self._action_calls.clear()
        self._action_response_queue.clear()
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

    def set_action_responses(self, responses: list[dict[str, Any]]) -> None:
        """
        Define a list of action response mocks.
        When an action is called that expects a response, the
        next response mock will be returned via FIFO queue.
        """
        self._action_response_queue = deque(responses)

    @override
    def check_health(self) -> bool:
        """Always returns True unless set manually to False"""
        return self._healthy

    @override
    def get_entity(self, entity_id: str) -> EntityData:
        """Get a mock entity by ID"""
        if entity_id not in self._entities:
            raise MockEntityDoesNotExistError(f"Entity {entity_id} doesn't exist")
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
        for timestamp_attr in ["last_changed", "last_reported", "last_updated"]:
            if timestamp_attr not in attributes:
                attributes[timestamp_attr] = now

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
            raise MockEntityDoesNotExistError(f"Entity {entity_id} doesn't exist")
        del self._entities[entity_id]

    @override
    def perform_action(
        self,
        domain: Domain,
        action: str,
        entity_id: str | list[str] | None = None,
        response_expected: bool = False,
        **body_params: Any,
    ) -> tuple[list[EntityData], dict[str, Any] | None]:
        """Record an action call and return mock entity states"""
        try:
            action_response = self._action_response_queue.popleft() if response_expected else None
        except IndexError:
            raise ValueError("No mocked action responses. Use mt.set_action_responses(...) first.")

        action_call = ActionCall(domain, action, action_response, entity_id, **body_params)
        self._action_calls.append(action_call)

        if entity_id is None:
            return [], action_response

        entity_ids = (
            [EntityId(id) for id in entity_id]
            if isinstance(entity_id, list)
            else [EntityId(entity_id)]
        )

        entities = [self._entities[id] for id in entity_ids if id in self._entities]

        return entities, action_response

    @override
    def execute_request(
        self,
        _method: HTTPMethod,
        _path: str,
        _body: dict | None = None,
        _params: dict | None = None,
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

    @override
    def lock(
        self,
        key: str,
        timeout_seconds: int = 10,
        exit_if_owned: bool = False,
    ) -> Lock | nullcontext:
        """Returns a nullcontext object for mock-friendly simulated lock context"""
        return nullcontext()


class MockJob:
    """Mock job object returned by MockJobScheduler"""

    def __init__(
        self,
        job_id: str,
        name: str,
        func: Callable[..., Any],
        kwargs: dict[str, Any],
        trigger: str | object | None = None,
        run_date: datetime | None = None,
    ):
        self.id = job_id
        self.name = name
        self.func = func
        self.kwargs = kwargs
        self.trigger = trigger
        self.run_date = run_date


class MockJobScheduler:
    """
    Mock APScheduler BackgroundScheduler for testing.
    Stores jobs in memory but doesn't actually execute them.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, MockJob] = {}

    def reset(self) -> None:
        """Clear all scheduled jobs"""
        self._jobs.clear()

    def add_job(
        self,
        func: Callable[..., Any],
        trigger: str | object | None = None,
        run_date: datetime | None = None,
        id: str | None = None,
        name: str | None = None,
        kwargs: dict[str, Any] | None = None,
        replace_existing: bool = False,
        **_trigger_args: Any,
    ) -> MockJob:
        """Mock add_job - stores job but doesn't schedule execution"""
        from uuid import uuid4

        job_id = id or str(uuid4())

        if job_id in self._jobs and not replace_existing:
            raise ValueError(f"Job {job_id} already exists")

        job = MockJob(
            job_id=job_id,
            name=name or str(getattr(func, "__name__", "unknown")),
            func=func,
            kwargs=kwargs or {},
            trigger=trigger,
            run_date=run_date,
        )

        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> MockJob:
        """Get a mock job by ID"""

        if job_id not in self._jobs:
            raise JobLookupError(job_id)

        return self._jobs[job_id]

    def get_jobs(self) -> list[MockJob]:
        """Get all scheduled jobs"""
        return list(self._jobs.values())

    def remove_job(self, job_id: str) -> None:
        """Remove a job by ID"""

        if job_id not in self._jobs:
            raise JobLookupError(job_id)

        del self._jobs[job_id]
