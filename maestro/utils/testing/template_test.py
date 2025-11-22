"""
Template for creating new Maestro automation tests.

Copy this file and modify it for your automation. Replace the TODOs
with your actual test logic.

Usage:
    1. Copy this file to your scripts directory or maestro/tests/
    2. Rename it to test_<your_automation>.py
    3. Replace TODOs with your test logic
    4. Run: make test TEST=path/to/your/test_file.py
"""

import pytest

from maestro.utils.testing import (
    assert_action_called,
    assert_job_scheduled,
    assert_notification_sent,
    maestro_test,
    simulate_event,
    simulate_state_change,
)


class TestYourAutomation:
    """Tests for [TODO: describe your automation]."""

    def test_state_change_trigger(self, maestro_test):
        """
        Test that [TODO: describe what should happen].

        Given: [TODO: describe initial state]
        When: [TODO: describe the trigger event]
        Then: [TODO: describe expected outcome]
        """
        # Setup: Add entities your automation needs
        # TODO: Replace with your entities
        maestro_test.add_entity("switch.my_device", state="off")
        maestro_test.add_entity("light.indicator", state="off")

        # Import: Import your automation module
        # TODO: Replace with your import
        # from scripts.my_automation import my_function

        # Act: Simulate the trigger event
        # TODO: Replace with your trigger
        simulate_state_change(
            entity_id="switch.my_device",
            from_state="off",
            to_state="on",
        )

        # Assert: Verify expected behavior
        # TODO: Replace with your assertions
        assert_action_called(
            entity_id="light.indicator",
            action="turn_on",
            hass_client=maestro_test.hass,
        )

    def test_event_trigger(self, maestro_test):
        """
        Test that [TODO: describe what should happen].

        Given: [TODO: describe initial state]
        When: [TODO: describe the event]
        Then: [TODO: describe expected outcome]
        """
        # Setup
        # TODO: Add your entities
        maestro_test.add_entity("switch.my_device", state="off")

        # Import
        # TODO: Import your automation
        # from scripts.my_automation import my_function

        # Act
        # TODO: Replace with your event
        simulate_event(event_type="my_custom_event", data={})

        # Assert
        # TODO: Replace with your assertions
        assert_action_called(
            entity_id="switch.my_device",
            action="turn_on",
            hass_client=maestro_test.hass,
        )

    def test_notification_sent(self, maestro_test):
        """
        Test that [TODO: describe notification behavior].

        Given: [TODO: describe initial state]
        When: [TODO: describe the trigger]
        Then: [TODO: describe notification expected]
        """
        # Setup
        # TODO: Add your entities
        maestro_test.add_entity("person.john", state="home")

        # Import
        # TODO: Import your automation
        # from scripts.my_automation import my_function

        # Act
        # TODO: Trigger your automation
        simulate_state_change("binary_sensor.door", "off", "on")

        # Assert
        # TODO: Verify notification
        assert_notification_sent(
            target_entity_id="person.john",
            title="Alert",
            message="Door opened",
        )

    def test_job_scheduled(self, maestro_test):
        """
        Test that [TODO: describe job scheduling behavior].

        Given: [TODO: describe initial state]
        When: [TODO: describe the trigger]
        Then: [TODO: describe job expected]
        """
        # Setup
        # TODO: Add your entities
        maestro_test.add_entity("switch.my_device", state="off")

        # Import
        # TODO: Import your automation
        # from scripts.my_automation import my_function

        # Act
        # TODO: Trigger your automation
        simulate_state_change("switch.my_device", "off", "on")

        # Assert
        # TODO: Verify job scheduled
        job = assert_job_scheduled(
            job_id="my_job_id",
            scheduler=maestro_test.scheduler,
            delay_hours=2,
        )

        # Optionally test the job's logic
        maestro_test.scheduler.execute_job(job.job_id)
        assert_action_called(
            entity_id="switch.my_device",
            action="turn_off",
            hass_client=maestro_test.hass,
        )

    def test_edge_case(self, maestro_test):
        """
        Test edge case: [TODO: describe edge case].

        This tests what happens when [TODO: describe unusual condition].
        """
        # Setup
        # TODO: Set up edge case conditions
        maestro_test.add_entity("switch.my_device", state="unavailable")

        # Import
        # TODO: Import your automation
        # from scripts.my_automation import my_function

        # Act
        # TODO: Trigger with edge case
        simulate_state_change("switch.my_device", "unavailable", "on")

        # Assert
        # TODO: Verify correct behavior
        # Example: Verify it handled the edge case gracefully
        from maestro.utils.testing import assert_action_not_called

        assert_action_not_called(
            entity_id="light.indicator",
            action="turn_on",
            hass_client=maestro_test.hass,
        )


# Additional test classes as needed
class TestYourAutomationIntegration:
    """Integration tests for [TODO: describe complex scenarios]."""

    def test_multi_step_workflow(self, maestro_test):
        """
        Test a complete workflow: [TODO: describe workflow].

        This tests the entire automation sequence from start to finish.
        """
        # Setup
        # TODO: Set up all required entities
        maestro_test.add_entity("switch.device1", state="off")
        maestro_test.add_entity("switch.device2", state="off")

        # Import
        # TODO: Import all related automations
        # from scripts.my_automation import function1, function2

        # Act - Step 1
        # TODO: First event
        simulate_state_change("switch.device1", "off", "on")

        # Assert - Step 1
        # TODO: Verify first step
        assert_action_called("switch.device2", "turn_on", hass_client=maestro_test.hass)

        # Clear action calls between steps if needed
        maestro_test.clear_action_calls()

        # Act - Step 2
        # TODO: Second event
        simulate_state_change("switch.device2", "on", "off")

        # Assert - Step 2
        # TODO: Verify second step
        assert_action_called("switch.device1", "turn_off", hass_client=maestro_test.hass)


# Tips:
# 1. Use clear, descriptive test names that explain what's being tested
# 2. Follow the Given-When-Then pattern in docstrings
# 3. Add entities BEFORE importing automations
# 4. Import automations INSIDE test functions, not at module level
# 5. One behavior per test method
# 6. Use assertion helpers for better error messages
# 7. Test edge cases (unavailable entities, missing data, etc.)
# 8. Group related tests in classes
