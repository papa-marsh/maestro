from datetime import timedelta

from maestro.domains import OFF, ON
from maestro.integrations import Domain
from maestro.testing import MaestroTest
from maestro.utils import local_now

from registry import binary_sensor, person, switch

from .. import ellie


def test_notify_ellie_wakeup(mt: MaestroTest) -> None:
    opened_at = local_now().replace(hour=4, minute=0, second=0, microsecond=0)
    closed_at = opened_at - timedelta(hours=7, minutes=42)

    mt.trigger_state_change(
        binary_sensor.ellie_bedroom_door,
        old=OFF,
        new=ON,
        old_attributes={"last_changed": closed_at},
        time_fired=opened_at,
    )

    message = "Ellie woke up at 4:00 after 7h 42m"
    mt.assert_action_called(
        Domain.NOTIFY,
        person.marshall.notify_action_name,
        message=message,
    )
    mt.assert_action_called(
        Domain.NOTIFY,
        person.emily.notify_action_name,
        message=message,
    )


def test_notify_ellie_wakeup_ignores_door_after_window(mt: MaestroTest) -> None:
    opened_at = local_now().replace(hour=8, minute=0, second=0, microsecond=0)

    mt.trigger_state_change(
        binary_sensor.ellie_bedroom_door,
        old=OFF,
        new=ON,
        old_attributes={"last_changed": opened_at - timedelta(hours=8)},
        time_fired=opened_at,
    )

    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)


def test_toggle_butterfly_light(mt: MaestroTest) -> None:
    # Light turns on when sound machine turns off
    mt.trigger_state_change(switch.ellies_sound_machine, new=OFF)
    mt.assert_action_called(
        domain=Domain.SWITCH,
        action="turn_on",
        entity_id=switch.butterfly_night_light.id,
    )

    # Light turns off when sound machine turns on
    mt.trigger_state_change(switch.ellies_sound_machine, new=ON)
    mt.assert_action_called(
        domain=Domain.SWITCH,
        action="turn_off",
        entity_id=switch.butterfly_night_light.id,
    )
