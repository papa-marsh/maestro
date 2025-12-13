from contextlib import suppress

import pytest

from maestro.domains import BinarySensor, Switch
from maestro.domains.entity import OFF, ON
from maestro.integrations.home_assistant.domain import Domain
from maestro.testing.maestro_test import MaestroTest
from maestro.utils.dates import local_now
from maestro.utils.exceptions import MockEntityDoesNotExistError


def test_set_and_get_state(mt: MaestroTest) -> None:
    mt.set_state("light.bedroom", ON)
    state = mt.get_state("light.bedroom")
    assert state == ON

    mt.set_state("light.bedroom", OFF)
    state = mt.get_state("light.bedroom")
    assert state == OFF


def test_set_state_with_attributes(mt: MaestroTest) -> None:
    mt.set_state("light.bedroom", ON, {"brightness": 255})
    brightness = mt.get_attribute("light.bedroom", "brightness", int)
    assert brightness == 255


def test_mock_client_action_tracking(mt: MaestroTest) -> None:
    """Test that mock client tracks action calls"""
    mt.set_state("light.bedroom", OFF)

    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
        brightness=255,
    )

    mt.assert_action_called(
        Domain.LIGHT,
        "turn_on",
        entity_id="light.bedroom",
        brightness=255,
    )


def test_action_call_filtering(mt: MaestroTest) -> None:
    """Test filtering action calls by various criteria"""
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_off",
        entity_id="light.kitchen",
    )
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_off",
        entity_id="light.kitchen",
    )
    mt.hass_client.perform_action(
        domain=Domain.SWITCH,
        action="turn_on",
        entity_id="switch.fan",
    )

    light_calls = mt.get_action_calls(domain=Domain.LIGHT)
    assert len(light_calls) == 3

    turn_on_calls = mt.get_action_calls(action="turn_on")
    assert len(turn_on_calls) == 2

    bedroom_calls = mt.get_action_calls(entity_id="light.bedroom")
    assert len(bedroom_calls) == 1


def test_clear_action_calls(mt: MaestroTest) -> None:
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )

    mt.assert_action_called(Domain.LIGHT, "turn_on")

    mt.clear_action_calls()

    mt.assert_action_not_called(Domain.LIGHT, "turn_on")


def test_assert_action_not_called(mt: MaestroTest) -> None:
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )

    mt.assert_action_not_called(Domain.LIGHT, "turn_off")


def test_assert_action_times(mt: MaestroTest) -> None:
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )

    mt.assert_action_called(Domain.LIGHT, "turn_on", call_count=2)


def test_assert_state(mt: MaestroTest) -> None:
    mt.set_state("light.bedroom", ON)
    mt.assert_state("light.bedroom", ON)


def test_assert_attribute(mt: MaestroTest) -> None:
    mt.set_state("light.bedroom", ON, {"brightness": 255})
    mt.assert_attribute("light.bedroom", "brightness", 255)


def test_reset_clears_state_and_actions(mt: MaestroTest) -> None:
    mt.set_state("light.bedroom", ON)
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )

    mt.reset()

    with suppress(MockEntityDoesNotExistError):
        mt.get_state("light.bedroom")
        assert False, "Expected ValueError for missing entity"

    mt.assert_action_not_called(Domain.LIGHT, "turn_on")


def test_set_attribute(mt: MaestroTest) -> None:
    mt.set_state("light.bedroom", ON, {"brightness": 100})
    mt.set_attribute("light.bedroom", "brightness", 255)
    brightness = mt.get_attribute("light.bedroom", "brightness", int)
    assert brightness == 255


def test_multiple_entities(mt: MaestroTest) -> None:
    mt.set_state("light.bedroom", ON)
    mt.set_state("light.kitchen", OFF)
    mt.set_state("switch.fan", OFF)

    mt.assert_state("light.bedroom", ON)
    mt.assert_state("light.kitchen", OFF)
    mt.assert_state("switch.fan", OFF)


def test_entity_with_complex_attributes(mt: MaestroTest) -> None:
    now = local_now()
    mt.set_state(
        "sensor.temperature",
        "72",
        {
            "unit": "°F",
            "battery": 90,
            "last_updated": now,
            "sensors": ["indoor", "outdoor"],
            "metadata": {"location": "bedroom"},
        },
    )

    unit = mt.get_attribute("sensor.temperature", "unit", str)
    assert unit == "°F"

    battery = mt.get_attribute("sensor.temperature", "battery", int)
    assert battery == 90

    sensors = mt.get_attribute("sensor.temperature", "sensors", list)
    assert sensors == ["indoor", "outdoor"]


def test_entity_auto_uses_mock_state_manager(mt: MaestroTest) -> None:
    """Test that entities automatically use the mock state manager"""

    switch = Switch("switch.test_switch")

    mt.set_state("switch.test_switch", OFF)

    assert switch.state == OFF
    assert switch.state_manager.redis_client is mt.redis_client


def test_entity_methods_are_tracked_automatically(mt: MaestroTest) -> None:
    """Test that entity action methods are automatically tracked"""

    switch = Switch("switch.test_switch")
    mt.set_state("switch.test_switch", OFF)

    switch.turn_on()

    mt.assert_action_called(Domain.SWITCH, "turn_on")


def test_entity_state_access_without_manual_mocking(mt: MaestroTest) -> None:
    """Test that entity state/attribute access works without manual setup"""

    switch = Switch("switch.bedroom")
    mt.set_state("switch.bedroom", ON, {"power_usage": 50})

    assert switch.state == ON

    power = mt.get_attribute(switch, "power_usage", int)
    assert power == 50


def test_multiple_entities_use_same_mock(mt: MaestroTest) -> None:
    """Test that multiple entities all use the same mock state manager"""

    sensor = BinarySensor("binary_sensor.motion")
    switch = Switch("switch.fan")

    mt.set_state("binary_sensor.motion", OFF)
    mt.set_state("switch.fan", OFF)

    assert sensor.state_manager.hass_client is switch.state_manager.hass_client
    assert sensor.state_manager.redis_client is mt.redis_client

    switch.turn_on()
    switch.turn_off()

    switch_calls = mt.get_action_calls(domain=Domain.SWITCH)
    assert len(switch_calls) == 2


def test_assert_entity_exists(mt: MaestroTest) -> None:
    """Test assert_entity_exists passes when entity exists"""
    with pytest.raises(AssertionError):
        mt.assert_entity_exists("light.bedroom")

    mt.set_state("light.bedroom", ON)
    mt.assert_entity_exists("light.bedroom")


def test_assert_entity_does_not_exist(mt: MaestroTest) -> None:
    """Test assert_entity_does_not_exist passes when entity doesn't exist"""
    mt.assert_entity_does_not_exist("light.nonexistent")

    mt.set_state("light.bedroom", ON)
    with pytest.raises(AssertionError):
        mt.assert_entity_does_not_exist("light.bedroom")


def test_job_scheduler_uses_mock(mt: MaestroTest) -> None:
    """Test that JobScheduler automatically uses mock in test mode"""
    from datetime import timedelta

    from maestro.utils.scheduler import JobScheduler

    def example_function() -> None:
        pass

    # Create JobScheduler without passing apscheduler - should auto-detect test mode
    scheduler = JobScheduler()

    # Schedule a job
    run_time = local_now() + timedelta(hours=1)
    job_id = scheduler.schedule_job(
        run_time=run_time,
        func=example_function,
    )

    # Verify it was scheduled in the mock
    mt.assert_job_scheduled(job_id, example_function)

    # Get the job and verify details
    job = mt.get_scheduled_job(job_id)
    assert job.func == example_function


def test_cancel_scheduled_job(mt: MaestroTest) -> None:
    """Test canceling a scheduled job"""
    from datetime import timedelta

    from maestro.utils.scheduler import JobScheduler

    def example_function() -> None:
        pass

    scheduler = JobScheduler()
    run_time = local_now() + timedelta(hours=1)
    job_id = scheduler.schedule_job(run_time, example_function)

    # Verify it was scheduled
    mt.assert_job_scheduled(job_id, example_function)

    # Cancel the job
    scheduler.cancel_job(job_id)

    # Verify it's no longer scheduled
    mt.assert_job_not_scheduled(job_id)


def test_get_all_scheduled_jobs(mt: MaestroTest) -> None:
    """Test getting all scheduled jobs"""
    from datetime import timedelta

    from maestro.utils.scheduler import JobScheduler

    def func1() -> None:
        pass

    def func2() -> None:
        pass

    scheduler = JobScheduler()
    run_time = local_now() + timedelta(hours=1)

    # Schedule multiple jobs
    job_id1 = scheduler.schedule_job(run_time, func1)
    job_id2 = scheduler.schedule_job(run_time, func2)

    # Get all jobs
    jobs = mt.get_scheduled_jobs()
    assert len(jobs) == 2

    job_ids = [job.id for job in jobs]
    assert job_id1 in job_ids
    assert job_id2 in job_ids


def test_scheduled_job_isolation_between_tests(mt: MaestroTest) -> None:
    """Test that scheduled jobs are cleared between tests"""
    from datetime import timedelta

    from maestro.utils.scheduler import JobScheduler

    def example_function() -> None:
        pass

    scheduler = JobScheduler()
    run_time = local_now() + timedelta(hours=1)

    # Schedule a job
    scheduler.schedule_job(run_time, example_function, job_id="isolation_test_job")

    # Verify it was scheduled
    mt.assert_job_scheduled("isolation_test_job", example_function)

    # Manually reset (simulating what happens between tests)
    mt.reset()

    # Verify the job is gone after reset
    mt.assert_job_not_scheduled("isolation_test_job")


def test_schedule_job_with_custom_id(mt: MaestroTest) -> None:
    """Test scheduling a job with a custom job ID"""
    from datetime import timedelta

    from maestro.utils.scheduler import JobScheduler

    def example_function() -> None:
        pass

    scheduler = JobScheduler()
    run_time = local_now() + timedelta(hours=1)
    custom_job_id = "my_custom_job_id"

    # Schedule with custom ID
    job_id = scheduler.schedule_job(run_time, example_function, job_id=custom_job_id)

    assert job_id == custom_job_id
    mt.assert_job_scheduled(custom_job_id, example_function)


def test_schedule_job_with_params(mt: MaestroTest) -> None:
    """Test scheduling a job with function parameters"""
    from datetime import timedelta

    from maestro.utils.scheduler import JobScheduler

    def example_function(param1: str, param2: int) -> None:
        pass

    scheduler = JobScheduler()
    run_time = local_now() + timedelta(hours=1)
    func_params = {"param1": "test", "param2": 42}

    job_id = scheduler.schedule_job(run_time, example_function, func_params=func_params)

    # Get the job and verify params were stored
    job = mt.get_scheduled_job(job_id)
    assert job.kwargs == func_params
