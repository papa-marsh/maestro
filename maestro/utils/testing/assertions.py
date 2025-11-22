"""Assertion helper functions for testing Maestro automations."""

from datetime import timedelta
from typing import Any

from maestro.integrations.home_assistant.domain import Domain
from maestro.utils.testing.mock_hass_client import ActionCall
from maestro.utils.testing.mock_notif import SentNotification, MockNotif
from maestro.utils.testing.mock_scheduler import ScheduledJob, MockJobScheduler


def assert_action_called(
    entity_id: str,
    action: str,
    hass_client: Any = None,
    times: int | None = None,
    **expected_params: Any,
) -> ActionCall:
    """
    Assert that a Home Assistant action was called on an entity.

    Args:
        entity_id: The entity ID the action should have been called on
        action: The action name (e.g., "turn_on", "turn_off")
        hass_client: The mock Home Assistant client (or use maestro_test.hass)
        times: Expected number of times the action was called (None = at least once)
        **expected_params: Additional parameters that should match the action call

    Returns:
        The ActionCall that matched (or the last one if multiple)

    Raises:
        AssertionError: If the action was not called as expected

    Example:
        >>> assert_action_called("switch.space_heater", "turn_off")
        >>> assert_action_called("light.bedroom", "turn_on", brightness=255)
        >>> assert_action_called("switch.fan", "toggle", times=2)
    """
    if hass_client is None:
        raise ValueError("Must provide hass_client parameter or use maestro_test.hass")

    calls = hass_client.get_action_calls_for_entity(entity_id)
    matching_calls = [
        call
        for call in calls
        if call.action == action
        and all(call.params.get(k) == v for k, v in expected_params.items())
    ]

    if times is not None:
        assert len(matching_calls) == times, (
            f"Expected {action} to be called {times} time(s) on {entity_id}, "
            f"but was called {len(matching_calls)} time(s)"
        )
    else:
        assert len(matching_calls) > 0, (
            f"Expected {action} to be called on {entity_id}, but it was not. "
            f"Available calls: {[call.action for call in calls]}"
        )

    return matching_calls[-1] if matching_calls else None


def assert_action_not_called(
    entity_id: str,
    action: str | None = None,
    hass_client: Any = None,
) -> None:
    """
    Assert that an action was NOT called on an entity.

    Args:
        entity_id: The entity ID to check
        action: Optional specific action name (if None, checks no actions at all)
        hass_client: The mock Home Assistant client

    Raises:
        AssertionError: If the action was called

    Example:
        >>> assert_action_not_called("switch.space_heater", "turn_on")
        >>> assert_action_not_called("light.bedroom")  # No actions at all
    """
    if hass_client is None:
        raise ValueError("Must provide hass_client parameter")

    calls = hass_client.get_action_calls_for_entity(entity_id)

    if action is None:
        assert len(calls) == 0, (
            f"Expected no actions on {entity_id}, but found: "
            f"{[call.action for call in calls]}"
        )
    else:
        matching_calls = [call for call in calls if call.action == action]
        assert len(matching_calls) == 0, (
            f"Expected {action} NOT to be called on {entity_id}, "
            f"but it was called {len(matching_calls)} time(s)"
        )


def assert_notification_sent(
    target_entity_id: str,
    title: str | None = None,
    message: str | None = None,
    priority: str | None = None,
    times: int | None = None,
) -> SentNotification:
    """
    Assert that a notification was sent to a target.

    Args:
        target_entity_id: The person entity ID (e.g., "person.marshall")
        title: Optional expected title (substring match)
        message: Optional expected message (substring match)
        priority: Optional expected priority
        times: Expected number of matching notifications (None = at least once)

    Returns:
        The SentNotification that matched (or the last one if multiple)

    Raises:
        AssertionError: If no matching notification was sent

    Example:
        >>> assert_notification_sent("person.marshall", title="Meeting")
        >>> assert_notification_sent("person.emily", message="Dad's In a Meeting")
    """
    notifications = MockNotif.get_notifications_for_target(target_entity_id)

    matching = [
        n
        for n in notifications
        if (title is None or title in n.title)
        and (message is None or message in n.message)
        and (priority is None or n.priority == priority)
    ]

    if times is not None:
        assert len(matching) == times, (
            f"Expected {times} notification(s) to {target_entity_id}, "
            f"but found {len(matching)}"
        )
    else:
        assert len(matching) > 0, (
            f"Expected notification to {target_entity_id} "
            f"(title={title}, message={message}, priority={priority}), "
            f"but none found. Sent notifications: {notifications}"
        )

    return matching[-1] if matching else None


def assert_notification_not_sent(
    target_entity_id: str | None = None,
    title: str | None = None,
    message: str | None = None,
) -> None:
    """
    Assert that a notification was NOT sent.

    Args:
        target_entity_id: Optional target to check (if None, checks no notifications at all)
        title: Optional title to check for
        message: Optional message to check for

    Raises:
        AssertionError: If a matching notification was sent

    Example:
        >>> assert_notification_not_sent("person.marshall")
        >>> assert_notification_not_sent()  # No notifications at all
    """
    if target_entity_id is None:
        all_notifications = MockNotif.get_sent_notifications()
        assert len(all_notifications) == 0, (
            f"Expected no notifications, but found {len(all_notifications)}"
        )
        return

    notifications = MockNotif.get_notifications_for_target(target_entity_id)

    if title is None and message is None:
        assert len(notifications) == 0, (
            f"Expected no notifications to {target_entity_id}, "
            f"but found {len(notifications)}"
        )
    else:
        matching = [
            n
            for n in notifications
            if (title is None or title in n.title) and (message is None or message in n.message)
        ]
        assert len(matching) == 0, (
            f"Expected no notification to {target_entity_id} "
            f"matching title={title}, message={message}, but found {len(matching)}"
        )


def assert_job_scheduled(
    job_id: str | None = None,
    func_name: str | None = None,
    scheduler: Any = None,
    delay_hours: float | None = None,
    delay_minutes: float | None = None,
) -> ScheduledJob:
    """
    Assert that a job was scheduled.

    Args:
        job_id: Optional specific job ID to check for
        func_name: Optional function name (substring match)
        scheduler: The mock scheduler instance
        delay_hours: Optional expected delay in hours (approximate)
        delay_minutes: Optional expected delay in minutes (approximate)

    Returns:
        The ScheduledJob that matched

    Raises:
        AssertionError: If no matching job was scheduled

    Example:
        >>> assert_job_scheduled(job_id="office_space_heater_auto_off")
        >>> assert_job_scheduled(func_name="turn_off_space_heater", delay_hours=2)
    """
    if scheduler is None:
        raise ValueError("Must provide scheduler parameter")

    if job_id is not None:
        job = scheduler.get_job(job_id)
        assert job is not None, f"Expected job with ID {job_id} to be scheduled, but it was not"
        return job

    jobs = scheduler.get_all_jobs()

    matching = [
        job for job in jobs if func_name is None or func_name in job.func_name
    ]

    assert len(matching) > 0, (
        f"Expected job with func_name containing '{func_name}', but found none. "
        f"Scheduled jobs: {[job.func_name for job in jobs]}"
    )

    job = matching[-1]

    # Check delay if specified
    if delay_hours is not None or delay_minutes is not None:
        expected_delay = timedelta(
            hours=delay_hours or 0,
            minutes=delay_minutes or 0,
        )
        actual_delay = job.run_time - job.scheduled_at

        # Allow 1 second tolerance for timing variations
        tolerance = timedelta(seconds=1)
        diff = abs(actual_delay - expected_delay)

        assert diff <= tolerance, (
            f"Expected job to be scheduled with delay of {expected_delay}, "
            f"but actual delay was {actual_delay} (diff: {diff})"
        )

    return job


def assert_job_not_scheduled(
    job_id: str | None = None,
    func_name: str | None = None,
    scheduler: Any = None,
) -> None:
    """
    Assert that a job was NOT scheduled.

    Args:
        job_id: Optional specific job ID to check
        func_name: Optional function name to check for
        scheduler: The mock scheduler instance

    Raises:
        AssertionError: If a matching job was scheduled

    Example:
        >>> assert_job_not_scheduled(job_id="office_space_heater_auto_off")
    """
    if scheduler is None:
        raise ValueError("Must provide scheduler parameter")

    if job_id is not None:
        job = scheduler.get_job(job_id)
        assert job is None, f"Expected job {job_id} NOT to be scheduled, but it was"
        return

    if func_name is not None:
        jobs = scheduler.get_all_jobs()
        matching = [job for job in jobs if func_name in job.func_name]
        assert len(matching) == 0, (
            f"Expected no job with func_name containing '{func_name}', "
            f"but found {len(matching)}"
        )


def assert_state_changed(
    entity_id: str,
    expected_state: str,
    hass_client: Any = None,
) -> None:
    """
    Assert that an entity's state changed to a specific value.

    Args:
        entity_id: The entity ID to check
        expected_state: The expected state value
        hass_client: The mock Home Assistant client

    Raises:
        AssertionError: If the state doesn't match

    Example:
        >>> assert_state_changed("switch.space_heater", "on")
    """
    if hass_client is None:
        raise ValueError("Must provide hass_client parameter")

    entity = hass_client.get_entity(entity_id)
    assert entity.state == expected_state, (
        f"Expected {entity_id} state to be '{expected_state}', "
        f"but it was '{entity.state}'"
    )


def assert_attribute_changed(
    entity_id: str,
    attribute: str,
    expected_value: Any,
    hass_client: Any = None,
) -> None:
    """
    Assert that an entity's attribute changed to a specific value.

    Args:
        entity_id: The entity ID to check
        attribute: The attribute name
        expected_value: The expected attribute value
        hass_client: The mock Home Assistant client

    Raises:
        AssertionError: If the attribute doesn't match

    Example:
        >>> assert_attribute_changed("light.bedroom", "brightness", 255)
    """
    if hass_client is None:
        raise ValueError("Must provide hass_client parameter")

    entity = hass_client.get_entity(entity_id)
    actual_value = entity.attributes.get(attribute)

    assert actual_value == expected_value, (
        f"Expected {entity_id}.{attribute} to be {expected_value}, "
        f"but it was {actual_value}"
    )
