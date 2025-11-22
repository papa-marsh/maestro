"""Trigger simulation utilities for testing Maestro automations."""

from datetime import datetime
from typing import Any

from maestro.integrations.home_assistant.types import (
    EntityData,
    EntityId,
    FiredEvent,
    NotifActionEvent,
    StateChangeEvent,
)
from maestro.utils.dates import local_now


def simulate_state_change(
    entity_id: str,
    from_state: str,
    to_state: str,
    old_attributes: dict[str, Any] | None = None,
    new_attributes: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
) -> StateChangeEvent:
    """
    Simulate a state change event and fire registered triggers.

    Args:
        entity_id: The entity ID (e.g., "switch.space_heater")
        from_state: The old state value
        to_state: The new state value
        old_attributes: Optional attributes for the old state
        new_attributes: Optional attributes for the new state
        timestamp: Optional timestamp (defaults to now)

    Returns:
        The StateChangeEvent that was fired

    Example:
        >>> event = simulate_state_change(
        ...     entity_id="switch.space_heater",
        ...     from_state="off",
        ...     to_state="on"
        ... )
    """
    from maestro.triggers.state_change import StateChangeTriggerManager

    timestamp = timestamp or local_now()
    old_attrs = old_attributes or {}
    new_attrs = new_attributes or {}

    # Ensure standard attributes are present
    if "last_changed" not in old_attrs:
        old_attrs["last_changed"] = timestamp
    if "last_updated" not in old_attrs:
        old_attrs["last_updated"] = timestamp
    if "last_changed" not in new_attrs:
        new_attrs["last_changed"] = timestamp
    if "last_updated" not in new_attrs:
        new_attrs["last_updated"] = timestamp

    old_data = EntityData(
        entity_id=EntityId(entity_id),
        state=from_state,
        attributes=old_attrs,
    )

    new_data = EntityData(
        entity_id=EntityId(entity_id),
        state=to_state,
        attributes=new_attrs,
    )

    state_change_event = StateChangeEvent(
        timestamp=timestamp,
        time_fired=timestamp,
        entity_id=EntityId(entity_id),
        old=old_data,
        new=new_data,
    )

    StateChangeTriggerManager.fire_triggers(state_change_event)

    return state_change_event


def simulate_event(
    event_type: str,
    data: dict[str, Any] | None = None,
    user_id: str | None = None,
    timestamp: datetime | None = None,
) -> FiredEvent:
    """
    Simulate a generic Home Assistant event and fire registered triggers.

    Args:
        event_type: The event type (e.g., "olivia_asleep")
        data: Optional event data dictionary
        user_id: Optional user ID who triggered the event
        timestamp: Optional timestamp (defaults to now)

    Returns:
        The FiredEvent that was fired

    Example:
        >>> event = simulate_event(
        ...     event_type="olivia_asleep",
        ...     data={"duration": 60}
        ... )
    """
    from maestro.triggers.event_fired import EventFiredTriggerManager

    timestamp = timestamp or local_now()
    data = data or {}

    fired_event = FiredEvent(
        timestamp=timestamp,
        time_fired=timestamp,
        type=event_type,
        data=data,
        user_id=user_id,
    )

    EventFiredTriggerManager.fire_triggers(fired_event)

    return fired_event


def simulate_notif_action(
    action_name: str,
    action_data: Any = None,
    device_id: str = "test_device_id",
    device_name: str = "Test Device",
    timestamp: datetime | None = None,
) -> NotifActionEvent:
    """
    Simulate a notification action button press and fire registered triggers.

    Args:
        action_name: The action identifier (e.g., "UNLOCK_DOOR")
        action_data: Optional data passed with the action
        device_id: Optional device identifier
        device_name: Optional device name
        timestamp: Optional timestamp (defaults to now)

    Returns:
        The NotifActionEvent that was fired

    Example:
        >>> event = simulate_notif_action(
        ...     action_name="UNLOCK_DOOR",
        ...     action_data={"door_id": "front_door"}
        ... )
    """
    from maestro.triggers.notif_action import NotifActionTriggerManager

    timestamp = timestamp or local_now()

    notif_action_event = NotifActionEvent(
        timestamp=timestamp,
        time_fired=timestamp,
        type="ios.notification_action_fired",
        data={},
        user_id=None,
        name=action_name,
        action_data=action_data,
        device_id=device_id,
        device_name=device_name,
    )

    NotifActionTriggerManager.fire_triggers(notif_action_event)

    return notif_action_event


def simulate_cron_trigger(func_name: str) -> None:
    """
    Simulate a cron trigger by directly calling the registered function.

    Note: This is a simple helper for testing scheduled functions.
    For more complex cron testing, call the function directly in your test.

    Args:
        func_name: The qualified name of the function to call

    Example:
        >>> from scripts.home.office.meetings import initialize_meeting_active_entity
        >>> simulate_cron_trigger("scripts.home.office.meetings.initialize_meeting_active_entity")
    """
    # For cron triggers, it's often simpler to just call the function directly
    # since they don't have event parameters
    raise NotImplementedError(
        "For cron triggers, call the function directly in your test. "
        "Cron triggers don't have event parameters, so direct invocation is cleaner."
    )
