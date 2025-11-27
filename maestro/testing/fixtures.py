from collections.abc import Generator

import pytest

from maestro.testing.maestro_test import MaestroTest


@pytest.fixture
def maestro_test() -> Generator[MaestroTest]:
    """
    Main pytest fixture providing a clean test context for each test.
    This fixture is automatically reset between tests, ensuring isolation.

    Usage:
        def test_my_automation(maestro_test: MaestroTest):
            maestro_test.set_state("light.bedroom", "off")
            maestro_test.trigger_state_change("switch.motion", "off", "on")
            maestro_test.assert_action_called("light", "turn_on")
    """
    context = MaestroTest()
    yield context
    context.reset()
