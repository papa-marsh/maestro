from unittest.mock import MagicMock, patch

from maestro.domains import HOME
from maestro.integrations import Domain
from maestro.testing import MaestroTest

from registry import person, zone

from .. import notifications

test_person = person.marshall
test_spouse = person.emily

job_id = notifications.JOB_ID_PREFIX + test_person.id.entity

test_location = zone.target
test_location_name = "Target"
test_debounced = zone.costco
test_debounced_name = "Costco"
test_region = zone.grand_rapids
test_region_name = "Grand Rapids"


@patch("scripts.location_tracking.notifications.set_last_left_home")
def test_location_update_orchestrator_basic(
    mock_set_last_left_home: MagicMock,
    mt: MaestroTest,
) -> None:
    # Needed for metadata lookup to fetch debounce
    mt.set_state(test_debounced, "test_state")
    mt.set_names(test_debounced, test_debounced_name)

    # Leaving home calls set_last_left_home(...)
    mt.trigger_state_change(test_person, old=HOME, new=test_region_name)
    assert mock_set_last_left_home.call_count == 1

    # Notif is sent immediately when zone doesn't have debounce
    mt.trigger_state_change(test_person, old=test_region_name, new=test_location_name)
    mt.assert_action_called(Domain.NOTIFY, test_spouse.notify_action_name)
    mt.assert_job_not_scheduled(job_id)


def test_location_update_orchestrator_debounce(mt: MaestroTest) -> None:
    # Future notif is scheduled when new zone has debounce
    mt.clear_action_calls()
    mt.trigger_state_change(test_person, old=test_region_name, new=test_debounced_name)
    mt.assert_action_not_called(Domain.NOTIFY, test_spouse.notify_action_name)
    mt.assert_job_scheduled(job_id, notifications.send_location_update)

    # Notif is suppressed when leaving zone that has debouncer job active
    mt.clear_action_calls()
    mt.trigger_state_change(test_person, old=test_region_name, new=test_debounced_name)
    mt.assert_job_scheduled(job_id, notifications.send_location_update)
    mt.trigger_state_change(test_person, old=test_debounced_name, new=test_region_name)
    mt.assert_job_not_scheduled(job_id)
    mt.assert_action_not_called(Domain.NOTIFY, test_spouse.notify_action_name)

    # Notif is sent when leaving a zone different from the debounced zone
    mt.clear_action_calls()
    mt.trigger_state_change(test_person, old=test_region_name, new=test_debounced_name)
    mt.assert_job_scheduled(job_id, notifications.send_location_update)
    mt.trigger_state_change(test_person, old=test_region_name, new=test_location_name)
    mt.assert_job_not_scheduled(job_id)
    mt.assert_action_called(Domain.NOTIFY, test_spouse.notify_action_name)


@patch("scripts.location_tracking.notifications.get_last_zone_arrival")
@patch("scripts.location_tracking.notifications.set_last_zone_arrival")
@patch("scripts.location_tracking.notifications.get_last_left_home")
@patch("scripts.location_tracking.notifications.set_last_left_home")
def test_send_location_update(
    mock_get_last_left_home: MagicMock,
    mock_get_last_zone_arrival: MagicMock,
    mock_set_last_left_home: MagicMock,
    mock_set_last_zone_arrival: MagicMock,
    mt: MaestroTest,
) -> None: ...
