import pytest

from maestro.domains.entity import Domain
from maestro.integrations.home_assistant_provider import EntityState, HomeAssistantProvider


class TestHomeAssistantProvider:
    @pytest.fixture(scope="class")
    def provider(self) -> HomeAssistantProvider:
        return HomeAssistantProvider()

    @pytest.fixture(scope="class", autouse=True)
    def check_health_or_skip(self, provider: HomeAssistantProvider) -> None:
        """Check Home Assistant health before running other tests. Skip all if unhealthy."""
        if not provider.check_health():
            pytest.skip("Home Assistant is not healthy - skipping all integration tests")

    def test_check_health(self, provider: HomeAssistantProvider) -> None:
        """Test that Home Assistant API is accessible and returns expected health response."""
        is_healthy = provider.check_health()
        assert is_healthy is True

    def test_get_state(self, provider: HomeAssistantProvider) -> None:
        entity_state = provider.get_state("person.marshall")

        assert isinstance(entity_state, EntityState)
        assert entity_state.entity_id == "person.marshall"
        assert isinstance(entity_state.state, str)
        assert isinstance(entity_state.attributes, dict)
        assert isinstance(entity_state.last_changed, str)
        assert isinstance(entity_state.last_reported, str)
        assert isinstance(entity_state.last_updated, str)

    def test_set_state(self, provider: HomeAssistantProvider) -> None:
        test_entity_id = "maestro.unit_test"
        provider.delete_entity_if_exists(test_entity_id)

        # Create a new entity
        entity_state, created = provider.set_state(test_entity_id, "test_state", {"test_attr": "test_value"})

        assert isinstance(entity_state, EntityState)
        assert created is True
        assert entity_state.entity_id == test_entity_id
        assert entity_state.state == "test_state"
        assert entity_state.attributes["test_attr"] == "test_value"

        # Update the existing entity
        entity_state, created = provider.set_state(
            test_entity_id, "updated_state", {"test_attr": "updated_value", "new_attr": "new_value"}
        )

        assert isinstance(entity_state, EntityState)
        assert created is False
        assert entity_state.entity_id == test_entity_id
        assert entity_state.state == "updated_state"
        assert entity_state.attributes["test_attr"] == "updated_value"
        assert entity_state.attributes["new_attr"] == "new_value"

    def test_perform_action(self, provider: HomeAssistantProvider) -> None:
        test_entity_id = "input_boolean.maestro_unit_test"
        # Get initial state
        initial_state = provider.get_state(test_entity_id)
        assert initial_state is not None
        initial_state_value = initial_state.state

        # Toggle the switch
        result_states = provider.perform_action(Domain.INPUT_BOOLEAN, "toggle", test_entity_id)

        assert isinstance(result_states, list)

        for state in result_states:
            assert isinstance(state, EntityState)

        # Get state after first toggle
        toggled_state = provider.get_state(test_entity_id)
        assert toggled_state is not None
        assert initial_state_value != toggled_state.state

        # Toggle back to original state
        provider.perform_action(Domain.INPUT_BOOLEAN, "toggle", test_entity_id)

        # Verify it's back to original state
        final_state = provider.get_state(test_entity_id)
        assert final_state is not None
        assert initial_state_value == final_state.state

    def test_delete_entity(self, provider: HomeAssistantProvider) -> None:
        test_entity_id = "maestro.unit_test_delete"
        # Create an entity to delete
        provider.set_state(test_entity_id, "to_be_deleted", {"delete_me": True})

        # Verify it exists
        entity_state = provider.get_state(test_entity_id)
        assert entity_state is not None

        # Delete the entity
        provider.delete_entity(test_entity_id)

        # Verify it no longer exists
        with pytest.raises(ValueError):
            provider.get_state(test_entity_id)
