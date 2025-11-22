"""Pytest fixtures for testing Maestro automations."""

from typing import Any, Generator
from unittest.mock import patch

import pytest

from maestro.integrations.home_assistant.types import EntityId
from maestro.triggers.trigger_manager import TriggerManager, initialize_trigger_registry
from maestro.utils.testing.mock_hass_client import MockHomeAssistantClient
from maestro.utils.testing.mock_notif import MockNotif
from maestro.utils.testing.mock_redis import MockRedisClient
from maestro.utils.testing.mock_scheduler import MockJobScheduler
from maestro.utils.testing.mock_state_manager import MockStateManager


class MaestroTestContext:
    """
    Test context providing access to all mock components and utilities.

    This gives tests a clean interface to interact with mocked components
    and set up test scenarios.
    """

    def __init__(
        self,
        hass_client: MockHomeAssistantClient,
        redis_client: MockRedisClient,
        state_manager: MockStateManager,
        scheduler: MockJobScheduler,
    ) -> None:
        self.hass = hass_client
        self.redis = redis_client
        self.state = state_manager
        self.scheduler = scheduler

    def add_entity(
        self,
        entity_id: str,
        state: str = "off",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a test entity to the mock Home Assistant instance.

        The entity will be available to your automation code and cached
        in the mock state manager.

        Args:
            entity_id: The entity ID (e.g., "switch.space_heater")
            state: Initial state value (default: "off")
            attributes: Optional attributes dictionary

        Example:
            >>> context.add_entity("switch.space_heater", state="off")
        """
        entity_data = self.hass.add_test_entity(entity_id, state, attributes)
        self.state.cache_entity(entity_data)

    def get_entity_state(self, entity_id: str) -> str:
        """Get the current state of an entity."""
        return self.hass.get_entity(entity_id).state

    def get_entity_attribute(self, entity_id: str, attribute: str) -> Any:
        """Get a specific attribute of an entity."""
        return self.hass.get_entity(entity_id).attributes.get(attribute)

    def get_action_calls(self) -> list:
        """Get all recorded Home Assistant action calls."""
        return self.hass.get_action_calls()

    def get_action_calls_for_entity(self, entity_id: str) -> list:
        """Get action calls for a specific entity."""
        return self.hass.get_action_calls_for_entity(entity_id)

    def get_sent_notifications(self) -> list:
        """Get all sent notifications."""
        return MockNotif.get_sent_notifications()

    def get_scheduled_jobs(self) -> list:
        """Get all scheduled jobs."""
        return self.scheduler.get_all_jobs()

    def clear_action_calls(self) -> None:
        """Clear recorded action calls between test steps."""
        self.hass.clear_action_calls()


@pytest.fixture
def maestro_test() -> Generator[MaestroTestContext, None, None]:
    """
    Primary test fixture providing a complete mocked Maestro environment.

    This fixture:
    - Creates isolated mock instances for all external dependencies
    - Sets up a test-specific trigger registry
    - Patches the real classes with mocks
    - Cleans up after the test completes

    Usage:
        def test_my_automation(maestro_test):
            # Add entities your automation needs
            maestro_test.add_entity("switch.space_heater", state="off")

            # Import your automation (this registers the triggers)
            from scripts.home.office import space_heater

            # Simulate events
            simulate_state_change("switch.space_heater", "off", "on")

            # Make assertions
            assert len(maestro_test.get_scheduled_jobs()) == 1
    """
    # Create mock instances
    mock_hass = MockHomeAssistantClient()
    mock_redis = MockRedisClient()
    mock_state_manager = MockStateManager(mock_hass, mock_redis)
    mock_scheduler = MockJobScheduler()

    # Set up test-specific trigger registry
    test_registry = initialize_trigger_registry()
    TriggerManager._test_registry = test_registry

    # Create context
    context = MaestroTestContext(mock_hass, mock_redis, mock_state_manager, mock_scheduler)

    # Patch all the real components with mocks
    patches = [
        patch("maestro.integrations.state_manager.StateManager", return_value=mock_state_manager),
        patch("maestro.integrations.home_assistant.client.HomeAssistantClient", return_value=mock_hass),
        patch("maestro.integrations.redis.RedisClient", return_value=mock_redis),
        patch("maestro.utils.scheduler.JobScheduler", return_value=mock_scheduler),
        patch("maestro.utils.push.Notif", MockNotif),
        # Patch Entity's state_manager property to use our mock
        patch("maestro.domains.entity.Entity.state_manager", mock_state_manager),
    ]

    # Start all patches
    for p in patches:
        p.start()

    try:
        yield context
    finally:
        # Stop all patches
        for p in patches:
            p.stop()

        # Clean up test registry
        if hasattr(TriggerManager, "_test_registry"):
            delattr(TriggerManager, "_test_registry")

        # Clear mock data
        mock_hass.clear_all()
        mock_redis.clear()
        mock_scheduler.clear()
        MockNotif.clear_sent_notifications()


@pytest.fixture
def mock_hass_client() -> MockHomeAssistantClient:
    """Standalone mock Home Assistant client fixture."""
    return MockHomeAssistantClient()


@pytest.fixture
def mock_redis_client() -> MockRedisClient:
    """Standalone mock Redis client fixture."""
    return MockRedisClient()


@pytest.fixture
def mock_state_manager(
    mock_hass_client: MockHomeAssistantClient,
    mock_redis_client: MockRedisClient,
) -> MockStateManager:
    """Standalone mock state manager fixture."""
    return MockStateManager(mock_hass_client, mock_redis_client)


@pytest.fixture
def mock_scheduler() -> MockJobScheduler:
    """Standalone mock job scheduler fixture."""
    return MockJobScheduler()
