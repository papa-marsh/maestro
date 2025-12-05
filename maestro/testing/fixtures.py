from collections.abc import Generator

import pytest
from flask import Flask

from maestro.testing.context import test_context
from maestro.testing.maestro_test import MaestroTest


@pytest.fixture
def maestro_test() -> Generator[MaestroTest]:
    """
    Main pytest fixture providing a clean test context for each test.
    This fixture is automatically reset between tests, ensuring isolation.
    All entities will automatically use the test's mock state manager.
    """
    # Create a minimal Flask app for trigger functions that need app context
    # We use a basic Flask app instead of MaestroFlask to avoid heavy initialization
    app = Flask("maestro_test")

    context = MaestroTest()
    app.scheduler = context.job_scheduler  # type: ignore[attr-defined]

    with app.app_context(), test_context(context.state_manager, context.job_scheduler):
        yield context
    context.reset()
