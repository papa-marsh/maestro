"""
Maestro Testing Framework

A comprehensive pytest-based testing framework for Maestro automations.

Usage:
    from maestro.utils.testing import (
        maestro_test,
        simulate_state_change,
        simulate_event,
        assert_action_called,
        assert_notification_sent,
    )

    def test_my_automation(maestro_test):
        # Set up test entities
        maestro_test.add_entity("switch.space_heater", state="off")

        # Import your automation
        from scripts.home.office import space_heater

        # Simulate events
        simulate_state_change("switch.space_heater", "off", "on")

        # Make assertions
        assert_action_called("switch.space_heater", "turn_on", hass_client=maestro_test.hass)
"""

# Main fixtures
from .fixtures import (
    MaestroTestContext,
    maestro_test,
    mock_hass_client,
    mock_redis_client,
    mock_scheduler,
    mock_state_manager,
)

# Trigger simulators
from .triggers import (
    simulate_event,
    simulate_notif_action,
    simulate_state_change,
)

# Assertion helpers
from .assertions import (
    assert_action_called,
    assert_action_not_called,
    assert_attribute_changed,
    assert_job_not_scheduled,
    assert_job_scheduled,
    assert_notification_not_sent,
    assert_notification_sent,
    assert_state_changed,
)

# Mock classes (for advanced usage)
from .mock_hass_client import ActionCall, MockHomeAssistantClient
from .mock_notif import MockNotif, SentNotification
from .mock_redis import MockRedisClient
from .mock_scheduler import MockJobScheduler, ScheduledJob
from .mock_state_manager import MockStateManager

__all__ = [
    # Main fixture
    "maestro_test",
    "MaestroTestContext",
    # Individual fixtures
    "mock_hass_client",
    "mock_redis_client",
    "mock_state_manager",
    "mock_scheduler",
    # Trigger simulators
    "simulate_state_change",
    "simulate_event",
    "simulate_notif_action",
    # Assertions
    "assert_action_called",
    "assert_action_not_called",
    "assert_notification_sent",
    "assert_notification_not_sent",
    "assert_job_scheduled",
    "assert_job_not_scheduled",
    "assert_state_changed",
    "assert_attribute_changed",
    # Mock classes
    "MockHomeAssistantClient",
    "MockRedisClient",
    "MockStateManager",
    "MockJobScheduler",
    "MockNotif",
    # Data classes
    "ActionCall",
    "SentNotification",
    "ScheduledJob",
]
