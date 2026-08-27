from maestro.domains import OFF, ON, UNAVAILABLE, UNKNOWN
from maestro.integrations import Domain
from maestro.testing import MaestroTest

from registry import maestro, person
from scripts.frontend.common.entity_card import RowColor
from scripts.vehicles.common import Nyx, Tess

from .. import bedtime_check
from ..doors import EXTERIOR_DOORS, GARAGE_STALLS


def initialize_bedtime_states(mt: MaestroTest) -> None:
    for door in [*EXTERIOR_DOORS, *GARAGE_STALLS]:
        mt.set_state(door, OFF)

    mt.set_state(
        maestro.entity_card_3,
        "All Shut",
        attributes={"blink": False, "row_3_color": RowColor.DEFAULT},
    )
    mt.set_state(Nyx.battery, "50")
    mt.set_state(Nyx.charger, OFF)
    mt.set_state(Tess.battery, "80")
    mt.set_state(Tess.charger, OFF)


def test_no_notification_when_nothing_needs_attention(mt: MaestroTest) -> None:
    initialize_bedtime_states(mt)

    bedtime_check.bedtime_check()

    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)


def test_combines_outstanding_tasks_for_both_people(mt: MaestroTest) -> None:
    initialize_bedtime_states(mt)
    mt.set_state(EXTERIOR_DOORS[0], ON, attributes={"friendly_name": "Front Door"})
    mt.set_state(GARAGE_STALLS[1], ON, attributes={"friendly_name": "West Stall"})
    mt.set_state(
        maestro.entity_card_3,
        "Front",
        attributes={"blink": True, "row_3_color": RowColor.RED},
    )
    mt.set_state(Nyx.battery, "49")

    bedtime_check.bedtime_check()

    message = "\n".join(
        [
            "• Front Door is open",
            "• West Stall is open",
            "• The garbage bins need to go out",
            "• Chelsea hasn't been fed",
            "• Nyx is unplugged at 49%",
        ]
    )
    mt.assert_action_called(
        Domain.NOTIFY,
        person.marshall.notify_action_name,
        title="Before Bed",
        message=message,
    )
    mt.assert_action_called(
        Domain.NOTIFY,
        person.emily.notify_action_name,
        title="Before Bed",
        message=message,
    )
    assert len(mt.get_action_calls(Domain.NOTIFY)) == 2


def test_ignores_low_batteries_when_plugged_in(mt: MaestroTest) -> None:
    initialize_bedtime_states(mt)
    mt.set_state(Nyx.battery, "10")
    mt.set_state(Nyx.charger, ON)
    mt.set_state(Tess.battery, "49.5")
    mt.set_state(Tess.charger, ON)

    bedtime_check.bedtime_check()

    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)


def test_ignores_unknown_and_unavailable_states(mt: MaestroTest) -> None:
    initialize_bedtime_states(mt)
    mt.set_state(EXTERIOR_DOORS[0], UNKNOWN)
    mt.set_state(GARAGE_STALLS[0], UNAVAILABLE)
    mt.set_state(EXTERIOR_DOORS[1], ON, attributes={"friendly_name": "Garage Door"})
    mt.set_state(maestro.entity_card_3, UNKNOWN)
    mt.set_state(Nyx.battery, UNKNOWN)
    mt.set_state(Tess.battery, UNAVAILABLE)

    bedtime_check.bedtime_check()

    for recipient in [person.marshall, person.emily]:
        mt.assert_action_called(
            Domain.NOTIFY,
            recipient.notify_action_name,
            message="• Garage Door is open",
        )
