from maestro.domains import OFF, ON
from maestro.integrations import Domain
from maestro.testing import MaestroTest

from registry import person, zone
from scripts.vehicles.common import Tess

from .. import sentry_reminder


def test_reminder_job_gets_set_and_cancelled(mt: MaestroTest) -> None:
    # Job gets scheduled when Tess arrives at the deprees
    mt.trigger_state_change(Tess.location, new=zone.the_deprees.entity_name)
    mt.assert_job_scheduled(sentry_reminder.SENTRY_REMINDER_JOB_ID, sentry_reminder.send_reminder)

    # Test job gets cancelled when Tess leaves
    mt.trigger_state_change(Tess.location, old=zone.the_deprees.entity_name)
    mt.assert_job_not_scheduled(sentry_reminder.SENTRY_REMINDER_JOB_ID)


def test_send_reminder_triggers_notif(mt: MaestroTest) -> None:
    # Notif doesn't fire if sentry is off
    mt.set_state(Tess.sentry_mode, OFF)
    sentry_reminder.send_reminder()
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)

    # Notif fires if sentry is on
    mt.set_state(Tess.sentry_mode, ON)
    sentry_reminder.send_reminder()
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)
