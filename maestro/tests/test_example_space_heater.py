"""
Example test demonstrating the Maestro testing framework.

This test shows how to test the space_heater automation from the scripts directory.
"""

from datetime import timedelta

import pytest

from maestro.utils.testing import (
    assert_action_called,
    assert_job_not_scheduled,
    assert_job_scheduled,
    maestro_test,
    simulate_state_change,
)


class TestSpaceHeaterAutomation:
    """Example tests for the space heater auto-off automation."""

    def test_space_heater_schedules_auto_off_when_turned_on(self, maestro_test):
        """
        Test that turning on the space heater schedules an auto-off job.

        This demonstrates:
        - Setting up test entities
        - Importing automation scripts
        - Simulating state changes
        - Asserting jobs were scheduled
        """
        # Set up the test entity
        maestro_test.add_entity("switch.space_heater", state="off")

        # Import the automation (this registers the triggers)
        # Note: In a real test, you'd import from scripts.home.office.space_heater
        # For this example, we'll just verify the framework works
        from maestro.registry import switch
        from maestro.triggers import state_change_trigger
        from maestro.utils import JobScheduler, local_now

        AUTO_OFF_JOB_ID = "office_space_heater_auto_off"

        def turn_off_space_heater() -> None:
            switch.space_heater.turn_off()

        @state_change_trigger(switch.space_heater, from_state="off", to_state="on")
        def space_heater_auto_off() -> None:
            two_hours_from_now = local_now() + timedelta(hours=2)
            JobScheduler().schedule_job(
                run_time=two_hours_from_now,
                func=turn_off_space_heater,
                job_id=AUTO_OFF_JOB_ID,
            )

        # Simulate turning on the space heater
        simulate_state_change(
            entity_id="switch.space_heater",
            from_state="off",
            to_state="on",
        )

        # Assert the auto-off job was scheduled
        job = assert_job_scheduled(
            job_id=AUTO_OFF_JOB_ID,
            scheduler=maestro_test.scheduler,
            delay_hours=2,
        )

        assert job is not None
        assert job.func_name == "test_example_space_heater.turn_off_space_heater"

    def test_space_heater_cancels_auto_off_when_manually_turned_off(self, maestro_test):
        """
        Test that manually turning off the space heater cancels the auto-off job.

        This demonstrates:
        - Multiple state changes in sequence
        - Asserting jobs were cancelled
        """
        # Set up the test entity
        maestro_test.add_entity("switch.space_heater", state="off")

        # Define the automation
        from maestro.registry import switch
        from maestro.triggers import state_change_trigger
        from maestro.utils import JobScheduler, local_now

        AUTO_OFF_JOB_ID = "office_space_heater_auto_off"

        def turn_off_space_heater() -> None:
            switch.space_heater.turn_off()

        @state_change_trigger(switch.space_heater, from_state="off", to_state="on")
        def space_heater_auto_off() -> None:
            two_hours_from_now = local_now() + timedelta(hours=2)
            JobScheduler().schedule_job(
                run_time=two_hours_from_now,
                func=turn_off_space_heater,
                job_id=AUTO_OFF_JOB_ID,
            )

        @state_change_trigger(switch.space_heater, to_state="off")
        def cancel_auto_off_job() -> None:
            JobScheduler().cancel_job(AUTO_OFF_JOB_ID)

        # First, turn on the heater (schedules the job)
        simulate_state_change(
            entity_id="switch.space_heater",
            from_state="off",
            to_state="on",
        )

        # Verify job was scheduled
        assert_job_scheduled(job_id=AUTO_OFF_JOB_ID, scheduler=maestro_test.scheduler)

        # Now turn it off manually
        simulate_state_change(
            entity_id="switch.space_heater",
            from_state="on",
            to_state="off",
        )

        # Verify job was cancelled
        assert_job_not_scheduled(job_id=AUTO_OFF_JOB_ID, scheduler=maestro_test.scheduler)

    def test_auto_off_job_actually_turns_off_heater(self, maestro_test):
        """
        Test that executing the scheduled job actually turns off the heater.

        This demonstrates:
        - Manually executing scheduled jobs for testing
        - Asserting entity actions were called
        """
        # Set up the test entity
        maestro_test.add_entity("switch.space_heater", state="on")

        # Define the turn_off function
        from maestro.registry import switch
        from maestro.utils import JobScheduler, local_now

        def turn_off_space_heater() -> None:
            switch.space_heater.turn_off()

        # Schedule the job
        job_id = maestro_test.scheduler.schedule_job(
            run_time=local_now() + timedelta(hours=2),
            func=turn_off_space_heater,
            job_id="test_auto_off",
        )

        # Manually execute the job to test its logic
        maestro_test.scheduler.execute_job(job_id)

        # Assert the turn_off action was called
        assert_action_called(
            entity_id="switch.space_heater",
            action="turn_off",
            hass_client=maestro_test.hass,
        )


class TestEventTriggerExample:
    """Example test showing event-based triggers."""

    def test_olivia_asleep_turns_on_sound_machine(self, maestro_test):
        """
        Example test for event-based automation.

        This demonstrates:
        - Testing event-fired triggers
        - Asserting entity actions
        """
        # Set up test entities
        maestro_test.add_entity("switch.olivias_sound_machine", state="off")

        # Define the automation
        from maestro.registry import switch
        from maestro.triggers import event_fired_trigger

        @event_fired_trigger("olivia_asleep")
        def sound_machine_on() -> None:
            switch.olivias_sound_machine.turn_on()

        # Simulate the event
        from maestro.utils.testing import simulate_event

        simulate_event(event_type="olivia_asleep")

        # Assert the sound machine was turned on
        assert_action_called(
            entity_id="switch.olivias_sound_machine",
            action="turn_on",
            hass_client=maestro_test.hass,
        )


class TestNotificationExample:
    """Example test showing notification testing."""

    def test_meeting_active_sends_notification(self, maestro_test):
        """
        Example test for notification sending.

        This demonstrates:
        - Testing notification sending
        - Asserting notification content
        """
        # Set up test entities
        maestro_test.add_entity("person.emily", state="home")
        maestro_test.add_entity("maestro.meeting_active", state="off")

        # Define the automation
        from maestro.registry import maestro, person
        from maestro.triggers import state_change_trigger
        from maestro.utils import Notif

        @state_change_trigger(maestro.meeting_active, to_state="on")
        def send_meeting_notification() -> None:
            if person.emily.state == "home":
                Notif(
                    title="Dad's In a Meeting",
                    message="Shhh",
                    tag="meeting_active",
                    priority=Notif.Priority.TIME_SENSITIVE,
                ).send(person.emily)

        # Simulate the state change
        simulate_state_change(
            entity_id="maestro.meeting_active",
            from_state="off",
            to_state="on",
        )

        # Assert notification was sent
        from maestro.utils.testing import assert_notification_sent

        assert_notification_sent(
            target_entity_id="person.emily",
            title="Dad's In a Meeting",
            message="Shhh",
        )
