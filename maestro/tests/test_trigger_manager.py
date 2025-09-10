from collections import defaultdict
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from maestro.integrations.home_assistant.types import EntityId, StateChangeEvent
from maestro.integrations.state_manager import StateManager
from maestro.triggers.state_change import StateChangeTriggerManager, state_change_trigger
from maestro.triggers.trigger_manager import (
    TriggerManager,
    TriggerType,
    initialize_trigger_registry,
)
from maestro.utils.dates import utc_now


class TestTriggerManager:
    def setup_method(self) -> None:
        """Use isolated test registry for each test"""
        TriggerManager._test_registry = initialize_trigger_registry()

    def teardown_method(self) -> None:
        """Clean up test registry"""
        if hasattr(TriggerManager, "_test_registry"):
            delattr(TriggerManager, "_test_registry")

    def test_register_function(self) -> None:
        """Test registering a function with the trigger manager"""

        def test_func() -> None:
            pass

        TriggerManager.register_function(
            trigger_type=TriggerType.STATE_CHANGE, registry_key="maestro.test", func=test_func
        )

        assert "maestro.test" in TriggerManager._test_registry[TriggerType.STATE_CHANGE]
        assert test_func in TriggerManager._test_registry[TriggerType.STATE_CHANGE]["maestro.test"]

    def test_register_multiple_functions_same_entity(self) -> None:
        """Test registering multiple functions for the same entity"""

        def func1() -> None:
            pass

        def func2() -> None:
            pass

        TriggerManager.register_function(
            trigger_type=TriggerType.STATE_CHANGE, registry_key="maestro.test", func=func1
        )
        TriggerManager.register_function(
            trigger_type=TriggerType.STATE_CHANGE, registry_key="maestro.test", func=func2
        )

        registered_funcs = TriggerManager._test_registry[TriggerType.STATE_CHANGE]["maestro.test"]
        assert len(registered_funcs) == 2
        assert func1 in registered_funcs
        assert func2 in registered_funcs

    def test_register_functions_different_entities(self) -> None:
        """Test registering functions for different entities"""

        def func1() -> None:
            pass

        def func2() -> None:
            pass

        TriggerManager.register_function(
            trigger_type=TriggerType.STATE_CHANGE, registry_key="maestro.test1", func=func1
        )
        TriggerManager.register_function(
            trigger_type=TriggerType.STATE_CHANGE, registry_key="maestro.test2", func=func2
        )

        assert func1 in TriggerManager._test_registry[TriggerType.STATE_CHANGE]["maestro.test1"]
        assert func2 in TriggerManager._test_registry[TriggerType.STATE_CHANGE]["maestro.test2"]
        assert len(TriggerManager._test_registry[TriggerType.STATE_CHANGE]) == 2

    def test_invoke_funcs_no_parameters(self) -> None:
        """Test invoking functions that take no parameters"""
        call_count = 0

        def test_func() -> None:
            nonlocal call_count
            call_count += 1

        from maestro.triggers.trigger_manager import StateChangeTriggerParams

        state_change = StateChangeEvent(
            timestamp=utc_now(),
            time_fired=utc_now(),
            event_type="state_changed",
            entity_id=EntityId("maestro.test"),
            old_state="off",
            new_state="on",
            old_attributes={},
            new_attributes={},
        )

        trigger_params = StateChangeTriggerParams(state_change=state_change)

        TriggerManager.invoke_funcs([test_func], trigger_params)
        assert call_count == 1

    def test_invoke_funcs_with_state_change_parameter(self) -> None:
        """Test invoking functions that take StateChangeEvent parameter"""
        received_state_change = None

        def test_func(state_change: StateChangeEvent) -> None:
            nonlocal received_state_change
            received_state_change = state_change

        from maestro.triggers.trigger_manager import StateChangeTriggerParams

        original_state_change = StateChangeEvent(
            timestamp=utc_now(),
            time_fired=utc_now(),
            event_type="state_changed",
            entity_id=EntityId("maestro.test"),
            old_state="off",
            new_state="on",
            old_attributes={},
            new_attributes={},
        )

        trigger_params = StateChangeTriggerParams(state_change=original_state_change)

        TriggerManager.invoke_funcs([test_func], trigger_params)
        assert received_state_change == original_state_change

    def test_invoke_funcs_invalid_parameter_name(self) -> None:
        """Test invoking function with invalid parameter name logs error but continues"""
        call_count = 0

        def test_func(_invalid_param: str) -> None:
            nonlocal call_count
            call_count += 1

        from maestro.triggers.trigger_manager import StateChangeTriggerParams

        state_change = StateChangeEvent(
            timestamp=utc_now(),
            time_fired=utc_now(),
            event_type="state_changed",
            entity_id=EntityId("maestro.test"),
            old_state="off",
            new_state="on",
            old_attributes={},
            new_attributes={},
        )

        trigger_params = StateChangeTriggerParams(state_change=state_change)

        with patch("maestro.triggers.trigger_manager.log") as mock_log:
            TriggerManager.invoke_funcs([test_func], trigger_params)
            mock_log.error.assert_called_once()
            # Function call will fail due to missing parameter and be caught by exception handler
            mock_log.exception.assert_called_once()
            assert call_count == 0

    @patch("maestro.triggers.trigger_manager.log")
    def test_invoke_funcs_exception_handling(self, mock_log: MagicMock) -> None:
        """Test that exceptions in trigger functions are logged but don't stop execution"""
        call_count = 0

        def failing_func() -> None:
            raise ValueError("Test error")

        def working_func() -> None:
            nonlocal call_count
            call_count += 1

        from maestro.triggers.trigger_manager import StateChangeTriggerParams

        state_change = StateChangeEvent(
            timestamp=utc_now(),
            time_fired=utc_now(),
            event_type="state_changed",
            entity_id=EntityId("maestro.test"),
            old_state="off",
            new_state="on",
            old_attributes={},
            new_attributes={},
        )

        trigger_params = StateChangeTriggerParams(state_change=state_change)

        TriggerManager.invoke_funcs([failing_func, working_func], trigger_params)

        # Verify exception was logged
        mock_log.exception.assert_called_once()
        # Verify second function still executed
        assert call_count == 1


class TestStateChangeTriggerManager:
    def setup_method(self) -> None:
        """Use isolated test registry for each test"""
        StateChangeTriggerManager._test_registry = {
            trig_type: defaultdict(list) for trig_type in TriggerType
        }

    def teardown_method(self) -> None:
        """Clean up test registry"""
        if hasattr(StateChangeTriggerManager, "_test_registry"):
            delattr(StateChangeTriggerManager, "_test_registry")

    def test_execute_triggers_no_registered_functions(self) -> None:
        """Test execute_triggers when no functions are registered for entity"""
        state_change = StateChangeEvent(
            timestamp=utc_now(),
            time_fired=utc_now(),
            event_type="state_changed",
            entity_id=EntityId("maestro.test"),
            old_state="off",
            new_state="on",
            old_attributes={},
            new_attributes={},
        )

        # Should not raise any errors
        StateChangeTriggerManager.execute_triggers(state_change)

    def test_execute_triggers_with_registered_functions(self) -> None:
        """Test execute_triggers calls registered functions"""
        call_count = 0
        received_state_change = None

        def test_func(state_change: StateChangeEvent) -> None:
            nonlocal call_count, received_state_change
            call_count += 1
            received_state_change = state_change

        # Manually register function
        StateChangeTriggerManager.register_function(
            trigger_type=TriggerType.STATE_CHANGE,
            registry_key=EntityId("maestro.test"),
            func=test_func,
        )

        state_change = StateChangeEvent(
            timestamp=utc_now(),
            time_fired=utc_now(),
            event_type="state_changed",
            entity_id=EntityId("maestro.test"),
            old_state="off",
            new_state="on",
            old_attributes={},
            new_attributes={},
        )

        StateChangeTriggerManager.execute_triggers(state_change)

        assert call_count == 1
        assert received_state_change == state_change

    def test_execute_triggers_multiple_functions(self) -> None:
        """Test execute_triggers calls multiple registered functions for same entity"""
        call_counts = [0, 0]

        def func1() -> None:
            call_counts[0] += 1

        def func2() -> None:
            call_counts[1] += 1

        entity_id = EntityId("maestro.test")

        # Register both functions
        StateChangeTriggerManager.register_function(
            trigger_type=TriggerType.STATE_CHANGE, registry_key=entity_id, func=func1
        )
        StateChangeTriggerManager.register_function(
            trigger_type=TriggerType.STATE_CHANGE, registry_key=entity_id, func=func2
        )

        state_change = StateChangeEvent(
            timestamp=utc_now(),
            time_fired=utc_now(),
            event_type="state_changed",
            entity_id=entity_id,
            old_state="off",
            new_state="on",
            old_attributes={},
            new_attributes={},
        )

        StateChangeTriggerManager.execute_triggers(state_change)

        assert call_counts[0] == 1
        assert call_counts[1] == 1


class TestStateChangeTriggerDecorator:
    def setup_method(self) -> None:
        """Use isolated test registry for each test"""
        StateChangeTriggerManager._test_registry = {
            trig_type: defaultdict(list) for trig_type in TriggerType
        }

    def teardown_method(self) -> None:
        """Clean up test registry"""
        if hasattr(StateChangeTriggerManager, "_test_registry"):
            delattr(StateChangeTriggerManager, "_test_registry")

    def test_decorator_registers_function_string_entity_id(self) -> None:
        """Test that decorator registers function with string entity ID"""

        @state_change_trigger("maestro.test")
        def test_func() -> None:
            pass

        entity_id = EntityId("maestro.test")
        # Verify function was registered in test registry
        registered_funcs = StateChangeTriggerManager._test_registry[TriggerType.STATE_CHANGE][
            entity_id
        ]
        assert len(registered_funcs) == 1
        assert registered_funcs[0].__name__ == "test_func"

        # Verify production registry is unaffected
        production_funcs = StateChangeTriggerManager.registry[TriggerType.STATE_CHANGE][entity_id]
        assert len(production_funcs) == 0

    def test_decorator_registers_function_entity_id_object(self) -> None:
        """Test that decorator registers function with EntityId object"""
        entity_id = EntityId("maestro.test")

        @state_change_trigger(entity_id)
        def test_func() -> None:
            pass

        registered_funcs = StateChangeTriggerManager._test_registry[TriggerType.STATE_CHANGE][
            entity_id
        ]
        assert len(registered_funcs) == 1
        assert registered_funcs[0].__name__ == "test_func"

    def test_decorator_preserves_function_metadata(self) -> None:
        """Test that decorator preserves original function metadata"""

        @state_change_trigger("maestro.test")
        def test_func() -> None:
            """Test docstring"""
            pass

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test docstring"

    def test_decorated_function_still_callable(self) -> None:
        """Test that decorated function can still be called directly"""
        call_count = 0

        @state_change_trigger("maestro.test")
        def test_func() -> None:
            nonlocal call_count
            call_count += 1

        test_func()
        assert call_count == 1

    def test_multiple_decorators_same_entity(self) -> None:
        """Test multiple functions decorated for same entity"""
        entity_id = EntityId("maestro.test")

        @state_change_trigger("maestro.test")
        def func1() -> None:
            pass

        @state_change_trigger("maestro.test")
        def func2() -> None:
            pass

        registered_funcs = StateChangeTriggerManager._test_registry[TriggerType.STATE_CHANGE][
            entity_id
        ]
        assert len(registered_funcs) == 2
        registered_names = [f.__name__ for f in registered_funcs]
        assert "func1" in registered_names
        assert "func2" in registered_names


class TestTriggerManagerIntegration:
    @pytest.fixture(scope="class")
    def state_manager(self) -> StateManager:
        return StateManager()

    @pytest.fixture(scope="class", autouse=True)
    def check_services_health_or_skip(self, state_manager: StateManager) -> None:
        """Check both Home Assistant and Redis health before running tests"""
        if not state_manager.hass_client.check_health():
            pytest.skip("Home Assistant is not healthy - skipping integration tests")
        if not state_manager.redis_client.check_health():
            pytest.skip("Redis is not healthy - skipping integration tests")

    def setup_method(self) -> None:
        """Use isolated test registry for each test"""
        StateChangeTriggerManager._test_registry = {
            trig_type: defaultdict(list) for trig_type in TriggerType
        }

    def teardown_method(self) -> None:
        """Clean up test registry"""
        if hasattr(StateChangeTriggerManager, "_test_registry"):
            delattr(StateChangeTriggerManager, "_test_registry")

    def test_trigger_execution_with_real_state_change(self, state_manager: StateManager) -> None:
        """Test trigger execution with real Home Assistant entity state change"""
        test_entity_id = EntityId("maestro.unit_test")
        call_log: list[dict[str, Any]] = []

        # Create test entity in Home Assistant
        state_manager.hass_client.set_entity(
            entity_id=test_entity_id,
            state="off",
            attributes={"friendly_name": "Unit Test Entity", "test_mode": True},
        )

        @state_change_trigger(test_entity_id)
        def trigger_func(state_change: StateChangeEvent) -> None:
            call_log.append(
                {
                    "entity_id": str(state_change.entity_id),
                    "old_state": state_change.old_state,
                    "new_state": state_change.new_state,
                    "timestamp": state_change.timestamp,
                }
            )

        # Create a state change event
        now = utc_now()
        state_change = StateChangeEvent(
            timestamp=now,
            time_fired=now,
            event_type="state_changed",
            entity_id=test_entity_id,
            old_state="off",
            new_state="on",
            old_attributes={"friendly_name": "Unit Test Entity", "test_mode": True},
            new_attributes={
                "friendly_name": "Unit Test Entity",
                "test_mode": True,
                "triggered": True,
            },
        )

        # Execute triggers
        StateChangeTriggerManager.execute_triggers(state_change)

        # Verify trigger was called
        assert len(call_log) == 1
        assert call_log[0]["entity_id"] == str(test_entity_id)
        assert call_log[0]["old_state"] == "off"
        assert call_log[0]["new_state"] == "on"
        assert call_log[0]["timestamp"] == now

        # Clean up
        state_manager.hass_client.delete_entity_if_exists(test_entity_id)

    def test_trigger_with_cached_state_change(self, state_manager: StateManager) -> None:
        """Test trigger execution when state change is cached"""
        test_entity_id = EntityId("maestro.unit_test")
        call_log: list[dict[str, Any]] = []

        # Create test entity
        state_manager.hass_client.set_entity(
            entity_id=test_entity_id,
            state="initial",
            attributes={"friendly_name": "Cache Test Entity"},
        )

        @state_change_trigger(test_entity_id)
        def cache_trigger(state_change: StateChangeEvent) -> None:
            call_log.append(
                {
                    "entity_id": str(state_change.entity_id),
                    "old_state": state_change.old_state,
                    "new_state": state_change.new_state,
                    "attributes": state_change.new_attributes,
                }
            )

        # Create state change event and cache it
        now = utc_now()
        state_change = StateChangeEvent(
            timestamp=now,
            time_fired=now,
            event_type="state_changed",
            entity_id=test_entity_id,
            old_state="initial",
            new_state="changed",
            old_attributes={"friendly_name": "Cache Test Entity"},
            new_attributes={
                "friendly_name": "Cache Test Entity",
                "last_triggered": now.isoformat(),
            },
        )

        # Cache the state change
        state_manager.cache_state_change(state_change)

        # Execute triggers
        StateChangeTriggerManager.execute_triggers(state_change)

        # Verify trigger was called with correct data
        assert len(call_log) == 1
        assert call_log[0]["entity_id"] == str(test_entity_id)
        assert call_log[0]["old_state"] == "initial"
        assert call_log[0]["new_state"] == "changed"
        attributes = call_log[0]["attributes"]
        assert attributes is not None and "last_triggered" in attributes

        # Verify state was cached correctly
        cached_state = state_manager.get_cached_state(test_entity_id)
        assert cached_state == "changed"

        # Clean up
        state_manager.hass_client.delete_entity_if_exists(test_entity_id)

    def test_multiple_triggers_same_entity_integration(self, state_manager: StateManager) -> None:
        """Test multiple triggers for same entity in integration scenario"""
        test_entity_id = EntityId("maestro.unit_test")
        call_logs: dict[str, list[str]] = {"func1": [], "func2": []}

        # Create test entity
        state_manager.hass_client.set_entity(
            entity_id=test_entity_id,
            state="ready",
            attributes={"friendly_name": "Multi Trigger Test"},
        )

        @state_change_trigger(test_entity_id)
        def multi_func1(state_change: StateChangeEvent) -> None:
            call_logs["func1"].append(f"State: {state_change.new_state}")

        @state_change_trigger(test_entity_id)
        def multi_func2() -> None:
            call_logs["func2"].append("Triggered")

        # Create state change
        state_change = StateChangeEvent(
            timestamp=utc_now(),
            time_fired=utc_now(),
            event_type="state_changed",
            entity_id=test_entity_id,
            old_state="ready",
            new_state="processing",
            old_attributes={"friendly_name": "Multi Trigger Test"},
            new_attributes={"friendly_name": "Multi Trigger Test", "status": "active"},
        )

        # Execute triggers
        StateChangeTriggerManager.execute_triggers(state_change)

        # Verify both functions were called
        assert len(call_logs["func1"]) == 1
        assert len(call_logs["func2"]) == 1
        assert call_logs["func1"][0] == "State: processing"
        assert call_logs["func2"][0] == "Triggered"

        # Clean up
        state_manager.hass_client.delete_entity_if_exists(test_entity_id)

    def test_trigger_error_handling_integration(self, state_manager: StateManager) -> None:
        """Test that trigger errors don't prevent other triggers from executing"""
        test_entity_id = EntityId("maestro.unit_test")
        call_log: list[str] = []

        # Create test entity
        state_manager.hass_client.set_entity(
            entity_id=test_entity_id,
            state="stable",
            attributes={"friendly_name": "Error Handling Test"},
        )

        @state_change_trigger(test_entity_id)
        def failing_trigger(_state_change: StateChangeEvent) -> None:
            raise ValueError("Intentional test error")

        @state_change_trigger(test_entity_id)
        def working_trigger(state_change: StateChangeEvent) -> None:
            call_log.append(f"Working: {state_change.new_state}")

        # Create state change
        state_change = StateChangeEvent(
            timestamp=utc_now(),
            time_fired=utc_now(),
            event_type="state_changed",
            entity_id=test_entity_id,
            old_state="stable",
            new_state="error_test",
            old_attributes={"friendly_name": "Error Handling Test"},
            new_attributes={"friendly_name": "Error Handling Test", "test_error": True},
        )

        # Execute triggers - should not raise exception
        with patch("maestro.triggers.trigger_manager.log") as mock_log:
            StateChangeTriggerManager.execute_triggers(state_change)

            # Verify error was logged
            mock_log.exception.assert_called_once()

        # Verify working trigger still executed
        assert len(call_log) == 1
        assert call_log[0] == "Working: error_test"

        # Clean up
        state_manager.hass_client.delete_entity_if_exists(test_entity_id)
