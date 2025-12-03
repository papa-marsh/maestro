import sys
import threading
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from maestro.utils.exceptions import TestFrameworkError

if TYPE_CHECKING:
    from maestro.integrations.state_manager import StateManager


_test_context = threading.local()


def test_mode_active(raise_without_test_context: bool = False) -> bool:
    """
    Returns True if pytest is loaded, False otherwise. Works before fixtures run.
    Use `require_test_context` to raise a runtime error if test context is not ready.
    """
    test_mode_active = "pytest" in sys.modules

    if test_mode_active and raise_without_test_context:
        get_test_state_manager()

    return test_mode_active


def set_test_state_manager(state_manager: "StateManager | None") -> None:
    """Set the active test state manager for the current test thread."""
    _test_context.state_manager = state_manager


def get_test_state_manager() -> "StateManager":
    """Get the test state manager of the current thread"""
    state_manager: StateManager | None = getattr(_test_context, "state_manager", None)

    if state_manager is None:
        raise TestFrameworkError("Couldn't find test state manager. Is the test context active?")

    return state_manager


@contextmanager
def test_context(state_manager: "StateManager") -> Generator["StateManager"]:
    """
    Context manager that activates test mode for the current thread.
    All state manager instances will use the test context's mocked state_manager.
    """
    set_test_state_manager(state_manager)
    try:
        yield state_manager
    finally:
        set_test_state_manager(None)
