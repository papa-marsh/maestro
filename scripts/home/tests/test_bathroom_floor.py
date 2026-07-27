from maestro.integrations import Domain
from maestro.testing import MaestroTest

from custom_domains import BathroomFloor
from registry import climate, person
from scripts.common.event_type import EventType
from scripts.config.secrets import PERSON_TO_USER_ID

from .. import bathroom_floor


def test_heat_bathroom_floor(mt: MaestroTest) -> None:
    # Firing event turns on heat and schedules jobs
    mt.trigger_event(EventType.BATHROOM_FLOOR, user_id=PERSON_TO_USER_ID[person.marshall])
    mt.assert_action_called(
        domain=Domain.CLIMATE,
        action="set_temperature",
        entity_id=climate.bathroom_floor_thermostat.id,
        target_temp=bathroom_floor.HEAT_TEMPERATURE,
    )
    mt.assert_job_scheduled(
        job_id=bathroom_floor.TEMPERATURE_CHECK_JOB_ID,
        func=bathroom_floor.check_floor_temp,
    )
    mt.assert_job_scheduled(
        job_id=bathroom_floor.TURN_OFF_HEAT_JOB_ID,
        func=bathroom_floor.reset_floor_to_auto,
    )


def test_reset_floor_to_auto(mt: MaestroTest) -> None:
    # Floor is set to auto when reset function executes
    bathroom_floor.reset_floor_to_auto()
    mt.assert_action_called(
        domain=Domain.CLIMATE,
        action="set_preset_mode",
        entity_id=climate.bathroom_floor_thermostat.id,
        preset_mode=BathroomFloor.PresetMode.RUN_SCHEDULE,
    )


def test_check_floor_temp(mt: MaestroTest) -> None:
    # If floor is ready, send notif and don't reschedule job
    mt.assert_job_not_scheduled(bathroom_floor.TEMPERATURE_CHECK_JOB_ID)
    mt.set_state(
        entity=climate.bathroom_floor_thermostat,
        state=BathroomFloor.PresetMode.PERMANENT_HOLD,
        attributes={"current_temperature": float(bathroom_floor.HEAT_TEMPERATURE)},
    )
    bathroom_floor.check_floor_temp(caller=person.marshall)
    mt.assert_job_not_scheduled(bathroom_floor.TEMPERATURE_CHECK_JOB_ID)
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)

    # If floor is not ready, don't send notif, reschedule job
    mt.clear_action_calls()
    mt.set_state(
        entity=climate.bathroom_floor_thermostat,
        state=BathroomFloor.PresetMode.PERMANENT_HOLD,
        attributes={"current_temperature": float(bathroom_floor.HEAT_TEMPERATURE - 10)},
    )
    bathroom_floor.check_floor_temp(caller=person.marshall)
    mt.assert_job_scheduled(
        job_id=bathroom_floor.TEMPERATURE_CHECK_JOB_ID,
        func=bathroom_floor.check_floor_temp,
    )
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)


def test_bathroom_floor_timeout_handler(mt: MaestroTest) -> None:
    # Event firing schedules auto shutoff job
    mt.trigger_state_change(
        entity=climate.bathroom_floor_thermostat,
        new=BathroomFloor.PresetMode.PERMANENT_HOLD,
    )
    mt.assert_job_scheduled(bathroom_floor.AUTO_SHUTOFF_JOB_ID, bathroom_floor.reset_after_timeout)

    # Floor going to auto mode cancels jobs
    mt.trigger_event(EventType.BATHROOM_FLOOR, user_id=PERSON_TO_USER_ID[person.marshall])
    mt.trigger_state_change(climate.bathroom_floor_thermostat, new=BathroomFloor.HVACMode.AUTO)
    mt.assert_job_not_scheduled(bathroom_floor.TEMPERATURE_CHECK_JOB_ID)
    mt.assert_job_not_scheduled(bathroom_floor.TURN_OFF_HEAT_JOB_ID)
    mt.assert_job_not_scheduled(bathroom_floor.AUTO_SHUTOFF_JOB_ID)


def test_reset_after_timeout(mt: MaestroTest) -> None:
    # Reset function sends notif and sets floor to auto
    bathroom_floor.reset_after_timeout()
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_called(
        domain=Domain.CLIMATE,
        action="set_preset_mode",
        entity_id=climate.bathroom_floor_thermostat.id,
        preset_mode=BathroomFloor.PresetMode.RUN_SCHEDULE,
    )
