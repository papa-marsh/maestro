from maestro.integrations import Domain
from maestro.testing import MaestroTest

from registry import switch

from .. import marshall


def test_bedtime(mt: MaestroTest) -> None:
    marshall.bedtime()

    mt.assert_action_called(
        domain=Domain.SWITCH,
        action="turn_on",
        entity_id=switch.master_sound_machine.id,
    )
