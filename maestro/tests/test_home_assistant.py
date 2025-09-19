from datetime import datetime

import pytest

from maestro.integrations.home_assistant.client import HomeAssistantClient
from maestro.integrations.home_assistant.types import Domain, EntityData


class TestHomeAssistantClient:
    @pytest.fixture(scope="class")
    def home_assistant_client(self) -> HomeAssistantClient:
        return HomeAssistantClient()

    @pytest.fixture(scope="class", autouse=True)
    def check_health_or_skip(self, home_assistant_client: HomeAssistantClient) -> None:
        """Check Home Assistant health before running other tests. Skip all if unhealthy"""
        if not home_assistant_client.check_health():
            pytest.skip("Home Assistant is not healthy - skipping all integration tests")

    def test_check_health(self, home_assistant_client: HomeAssistantClient) -> None:
        """Test that Home Assistant API is accessible and returns expected health response"""
        is_healthy = home_assistant_client.check_health()
        assert is_healthy is True

    def test_get_entity(self, home_assistant_client: HomeAssistantClient) -> None:
        entity = home_assistant_client.get_entity("person.marshall")

        assert isinstance(entity, EntityData)
        assert entity.entity_id == "person.marshall"
        assert isinstance(entity.state, str)
        assert isinstance(entity.attributes, dict)
        assert isinstance(entity.attributes["last_changed"], datetime)
        assert isinstance(entity.attributes["last_reported"], datetime)
        assert isinstance(entity.attributes["last_updated"], datetime)

    def test_set_entity(self, home_assistant_client: HomeAssistantClient) -> None:
        test_entity_id = "maestro.unit_test"
        home_assistant_client.delete_entity_if_exists(test_entity_id)

        # Create a new entity
        entity, created = home_assistant_client.set_entity(
            entity_id=test_entity_id,
            state="test_state",
            attributes={"test_attr": "test_value"},
        )

        assert isinstance(entity, EntityData)
        assert created is True
        assert entity.entity_id == test_entity_id
        assert entity.state == "test_state"
        assert entity.attributes["test_attr"] == "test_value"

        # Update the existing entity
        entity, created = home_assistant_client.set_entity(
            entity_id=test_entity_id,
            state="updated_state",
            attributes={"test_attr": "updated_value", "new_attr": "new_value"},
        )

        assert isinstance(entity, EntityData)
        assert created is False
        assert entity.entity_id == test_entity_id
        assert entity.state == "updated_state"
        assert entity.attributes["test_attr"] == "updated_value"
        assert entity.attributes["new_attr"] == "new_value"

    def test_perform_action(self, home_assistant_client: HomeAssistantClient) -> None:
        test_entity_id = "input_boolean.maestro_unit_test"
        # Get initial state
        initial_state = home_assistant_client.get_entity(test_entity_id)
        assert initial_state is not None
        initial_state_value = initial_state.state

        # Toggle the switch
        result_states = home_assistant_client.perform_action(
            Domain.INPUT_BOOLEAN, "toggle", test_entity_id
        )

        assert isinstance(result_states, list)

        for state in result_states:
            assert isinstance(state, EntityData)

        # Get state after first toggle
        toggled_state = home_assistant_client.get_entity(test_entity_id)
        assert toggled_state is not None
        assert initial_state_value != toggled_state.state

        # Toggle back to original state
        home_assistant_client.perform_action(Domain.INPUT_BOOLEAN, "toggle", test_entity_id)

        # Verify it's back to original state
        final_state = home_assistant_client.get_entity(test_entity_id)
        assert final_state is not None
        assert initial_state_value == final_state.state

    def test_delete_entity(self, home_assistant_client: HomeAssistantClient) -> None:
        test_entity_id = "maestro.unit_test_delete"
        # Create an entity to delete
        home_assistant_client.set_entity(test_entity_id, "to_be_deleted", {"delete_me": True})

        # Verify it exists
        entity = home_assistant_client.get_entity(test_entity_id)
        assert entity is not None

        # Delete the entity
        home_assistant_client.delete_entity(test_entity_id)

        # Verify it no longer exists
        with pytest.raises(ValueError):
            home_assistant_client.get_entity(test_entity_id)
