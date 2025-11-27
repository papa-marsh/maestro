from collections.abc import Generator

import pytest

from maestro.testing.context import test_context
from maestro.testing.maestro_test import MaestroTest


@pytest.fixture
def maestro_test() -> Generator[MaestroTest]:
    """
    Main pytest fixture providing a clean test context for each test.
    This fixture is automatically reset between tests, ensuring isolation.
    All entities will automatically use the test's mock state manager.
    """
    context = MaestroTest()
    with test_context(context.state_manager):
        yield context
    context.reset()
