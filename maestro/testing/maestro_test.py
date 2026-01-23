from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from typing import Any

from apscheduler.jobstores.base import JobLookupError  # type:ignore[import-untyped]
from freezegun import freeze_time

from maestro.config import TIMEZONE
from maestro.domains.entity import Entity
from maestro.handlers.types import EventTypeName
from maestro.integrations.home_assistant.domain import Domain
from maestro.integrations.home_assistant.types import (
    AttributeId,
    EntityData,
    EntityId,
    FiredEvent,
    NotifActionEvent,
    StateChangeEvent,
)
from maestro.integrations.redis import CachedValueT
from maestro.testing.context import get_test_job_scheduler, get_test_state_manager
from maestro.testing.mocks import ActionCall, MockHomeAssistantClient, MockJob, MockRedisClient
from maestro.triggers.event_fired import EventFiredTriggerManager
from maestro.triggers.hass import HassEvent, HassTriggerManager
from maestro.triggers.maestro import MaestroEvent, MaestroTriggerManager
from maestro.triggers.notif_action import NotifActionTriggerManager
from maestro.triggers.state_change import StateChangeTriggerManager
from maestro.utils.dates import local_now
from maestro.utils.exceptions import MockEntityDoesNotExistError, UnitTestFrameworkError


class MaestroTest:
    def __init__(self) -> None:
        self.job_scheduler = get_test_job_scheduler()
        self.state_manager = get_test_state_manager()

        if not isinstance(self.state_manager.hass_client, MockHomeAssistantClient):
            raise UnitTestFrameworkError
        if not isinstance(self.state_manager.redis_client, MockRedisClient):
            raise UnitTestFrameworkError

        self.hass_client = self.state_manager.hass_client
        self.redis_client = self.state_manager.redis_client

    def reset(self) -> None:
        """Reset mock state and action call history"""
        self.hass_client.reset()
        self.redis_client.reset()
        self.job_scheduler.reset()

    # MARK: Entity State Setup

    def set_state(
        self,
        entity: Entity | str,
        state: str,
        attributes: dict[str, CachedValueT] | None = None,
    ) -> EntityData:
        """Set the state of an entity for testing. Accepts an entity or entity ID string."""
        entity_id = entity.id if isinstance(entity, Entity) else EntityId(entity)

        return self.state_manager.post_hass_entity(
            entity_id=entity_id,
            state=state,
            attributes=attributes or {},
        )

    def get_state(self, entity: Entity | str) -> str:
        """Get the current state of an entity. Accepts an entity or entity ID string."""
        entity_id = entity.id if isinstance(entity, Entity) else EntityId(entity)

        return self.state_manager.get_entity_state(entity_id)

    def get_attribute(self, entity: Entity | str, attribute: str, expected_type: type) -> Any:
        """Get an attribute value from an entity. Accepts an entity or entity ID string."""
        entity_id = entity.id if isinstance(entity, Entity) else EntityId(entity)
        attribute_id = AttributeId(f"{entity_id}.{attribute}")
        return self.state_manager.get_attribute_state(attribute_id, expected_type)

    def set_attribute(self, entity: Entity | str, attribute: str, value: Any) -> None:
        """Set an attribute value on an entity."""
        entity_id = entity.id if isinstance(entity, Entity) else EntityId(entity)
        entity_data = self.state_manager.fetch_hass_entity(entity_id)
        entity_data.attributes[attribute] = value

        self.state_manager.cache_entity(entity_data)

    def set_action_responses(self, responses: list[dict[str, Any]]) -> None:
        """Mock the responses returned in order whenever a performed action expects a response"""
        self.hass_client.set_action_responses(responses)

    # MARK: Trigger Simulation

    def trigger_state_change(
        self,
        entity: Entity | str,
        old: str = "",
        new: str = "",
        old_attributes: dict[str, Any] | None = None,
        new_attributes: dict[str, Any] | None = None,
        time_fired: datetime | None = None,
    ) -> None:
        """Simulate a state change event, triggering any registered state_change_triggers."""
        entity_id = entity.id if isinstance(entity, Entity) else EntityId(entity)
        timestamp = time_fired or local_now()

        if not old:
            with suppress(MockEntityDoesNotExistError):
                old = self.get_state(entity_id)

        old_data = EntityData(
            entity_id=entity_id,
            state=old,
            attributes=old_attributes or {},
        )

        new_data = EntityData(
            entity_id=entity_id,
            state=new,
            attributes=new_attributes or {},
        )

        self.set_state(entity_id, new, new_attributes)

        state_change = StateChangeEvent(
            time_fired=timestamp,
            type=EventTypeName.STATE_CHANGED,
            data={},
            user_id="",
            entity_id=entity_id,
            old=old_data,
            new=new_data,
        )

        StateChangeTriggerManager.fire_triggers(state_change)

    def trigger_event(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
        user_id: str | None = None,
        time_fired: datetime | None = None,
    ) -> None:
        """Simulate a Home Assistant event, triggering any registered event_fired_triggers."""
        timestamp = time_fired or local_now()

        event = FiredEvent(
            time_fired=timestamp,
            type=event_type,
            data=data or {},
            user_id=user_id,
        )

        EventFiredTriggerManager.fire_triggers(event)

    def trigger_notif_action(
        self,
        action: str,
        action_data: Any = None,
        device_id: str = "test_device",
        device_name: str = "Test Device",
        time_fired: datetime | None = None,
    ) -> None:
        """Simulate a notification action event, triggering registered notif_action_triggers."""
        timestamp = time_fired or local_now()

        notif_action = NotifActionEvent(
            time_fired=timestamp,
            type="ios.notification_action_fired",
            data={},
            user_id=None,
            name=action,
            action_data=action_data,
            device_id=device_id,
            device_name=device_name,
        )

        NotifActionTriggerManager.fire_triggers(notif_action)

    def trigger_maestro_event(self, event: MaestroEvent) -> None:
        """Simulate a Maestro lifecycle event (e.g. startup or shutdown)."""
        MaestroTriggerManager.fire_triggers(event)

    def trigger_hass_event(self, event: HassEvent) -> None:
        """Simulate a Home Assistant lifecycle event (e.g. startup or shutdown)."""
        HassTriggerManager.fire_triggers(event)

    # MARK: Action Call Assertions

    def get_action_calls(
        self,
        domain: Domain | None = None,
        action: str | None = None,
        entity_id: str | None = None,
    ) -> list[ActionCall]:
        """Get all recorded action calls, optionally filtered.

        Args:
            domain: Filter by domain (e.g., "light", Domain.LIGHT)
            action: Filter by action name (e.g., "turn_on")
            entity_id: Filter by entity_id
        """
        return self.hass_client.get_action_calls(domain, action, entity_id)

    def assert_action_called(
        self,
        domain: Domain,
        action: str,
        entity_id: str | None = None,
        call_count: int | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Assert that an action was called with the specified parameters.

        Args:
            domain: The domain (e.g., "light", Domain.LIGHT)
            action: The action name (e.g., "turn_on")
            entity_id: Optional entity_id to filter by
            call_count: Optional expected number of times called (if None, asserts at least once)
            **kwargs: Optional action parameters to match
        """
        calls = self.get_action_calls(domain, action, entity_id)

        if kwargs:
            calls = [
                call for call in calls if all(call.kwargs.get(k) == v for k, v in kwargs.items())
            ]

        if call_count is not None:
            assert len(calls) == call_count, (
                f"Expected {domain}.{action} to be called {call_count} times, "
                f"but it was called {len(calls)} times. Calls: {calls}"
            )
        else:
            assert len(calls) > 0, (
                f"Expected {domain}.{action} to be called at least once, "
                f"but it was never called. All calls: {self.hass_client._action_calls}"
            )

    def assert_action_not_called(
        self,
        domain: Domain,
        action: str,
        entity_id: str | None = None,
    ) -> None:
        """
        Assert that an action was NOT called.

        Args:
            domain: The domain (e.g., "light", Domain.LIGHT)
            action: The action name (e.g., "turn_on")
            entity_id: Optional entity_id to filter by
        """
        calls = self.get_action_calls(domain, action, entity_id)
        assert len(calls) == 0, (
            f"Expected {domain}.{action} to NOT be called, "
            f"but it was called {len(calls)} times. Calls: {calls}"
        )

    def clear_action_calls(self) -> None:
        """
        Clear all recorded action calls.
        Useful for testing multiple scenarios in the same test.
        """
        self.hass_client.clear_action_calls()

    # MARK: Entity Assertions

    def assert_entity_exists(self, entity: Entity | str) -> None:
        """Assert that an entity exists in the mock home assistant client."""
        entity_id = entity.id if isinstance(entity, Entity) else entity
        try:
            self.get_state(entity)
        except MockEntityDoesNotExistError:
            assert False, f"Expected entity {entity_id} to exist, but it doesn't"

    def assert_entity_does_not_exist(self, entity: Entity | str) -> None:
        """Assert that an entity does not exist in the mock home assistant client."""
        entity_id = entity.id if isinstance(entity, Entity) else entity
        with suppress(MockEntityDoesNotExistError):
            state = self.get_state(entity)
            assert False, f"Expected entity {entity_id} to not exist, but it has state '{state}'"

    def assert_state(self, entity: Entity | str, expected_state: str) -> None:
        """Assert that an entity has a specific state."""
        actual_state = self.get_state(entity)
        assert actual_state == expected_state, (
            f"Expected state '{expected_state}' but got '{actual_state}'"
        )

    def assert_attribute(
        self,
        entity: Entity | str,
        attribute: str,
        expected_value: CachedValueT,
    ) -> None:
        """Assert that an entity attribute has a specific value."""
        expected_type = type(expected_value)
        actual_value = self.get_attribute(entity, attribute, expected_type)
        assert actual_value == expected_value, (
            f"Expected attribute '{attribute}' to be '{expected_value}' but got '{actual_value}'"
        )

    # MARK: Job Scheduler Assertions

    def assert_job_scheduled(
        self,
        job_id: str,
        func: Callable[..., Any],
        run_time: datetime | None = None,
    ) -> None:
        """Assert that a job with the given ID has been scheduled."""
        job = self.job_scheduler.get_job(job_id)
        job_func_name = f"{job.func.__module__}.{job.func.__name__}"
        func_name = f"{func.__module__}.{func.__name__}"
        assert job is not None, f"Expected job {job_id} to be scheduled but it wasn't"
        assert job.func == func, f"Expected job to have func {func_name} but got {job_func_name}"
        if run_time is not None:
            assert job.run_date == run_time, f"Expected run time {run_time} but got {job.run_date}"

    def assert_job_not_scheduled(self, job_id: str) -> None:
        """Assert that a job with the given ID has NOT been scheduled."""
        with suppress(JobLookupError):
            self.job_scheduler.get_job(job_id)
            assert False, f"Expected job {job_id} to NOT be scheduled, but it was"

    def get_scheduled_jobs(self) -> list[MockJob]:
        """Get all scheduled jobs from the mock scheduler."""
        return self.job_scheduler.get_jobs()

    def get_scheduled_job(self, job_id: str) -> MockJob:
        """Get a specific scheduled job by ID."""
        return self.job_scheduler.get_job(job_id)

    # MARK: Time Mocking

    def mock_datetime_as(self, frozen_time: datetime | str | None = None) -> Any:
        """Wrapper around freeze_time that supports local_now() and handles timezone weirdness."""
        if frozen_time is None:
            return freeze_time()

        if isinstance(frozen_time, str):
            frozen_time = datetime.fromisoformat(frozen_time)

        if frozen_time.tzinfo is None:
            frozen_time = frozen_time.replace(tzinfo=TIMEZONE)
        elif frozen_time.tzinfo != TIMEZONE:
            frozen_time = frozen_time.astimezone(TIMEZONE)

        tz_offset = frozen_time.utcoffset()
        if tz_offset is None:
            raise ValueError("Timezone offset is None, even after timezone processing")

        return freeze_time(frozen_time, tz_offset=tz_offset)
