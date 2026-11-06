import pytest
from maestro.domains import AWAY, HOME
from maestro.integrations import Domain
from maestro.testing import MaestroTest

from registry import person, switch
from scripts.common.event_type import EventType

from .. import olivia


@pytest.mark.parametrize("emily_state", [HOME, AWAY])
def test_toggle_sound_machine(mt: MaestroTest, emily_state: str) -> None:
    """Follow Olivia's sleep events regardless of Emily's location."""
    mt.set_state(person.emily, emily_state)
    mt.trigger_event(EventType.OLIVIA_ASLEEP)
    mt.assert_action_called(
        domain=Domain.SWITCH,
        action="turn_on",
        entity_id=switch.olivias_sound_machine.id,
    )

    # Sound machine turns off for 'olivia_awake' event
    mt.trigger_event(EventType.OLIVIA_AWAKE)
    mt.assert_action_called(
        domain=Domain.SWITCH,
        action="turn_off",
        entity_id=switch.olivias_sound_machine.id,
    )
