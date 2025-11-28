import sys
import threading
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from maestro.integrations.state_manager import StateManager

# Thread-local storage for test context
_test_context = threading.local()


def test_mode_active() -> bool:
    """Returns True if pytest is loaded, False otherwise. Works before fixtures run."""
    return "pytest" in sys.modules


def raise_for_missing_test_context() -> None:
    """Raise a runtime error if test context is not active and ready."""
    if not test_mode_active():
        raise RuntimeError("Test mode is not active")

    if get_test_state_manager() is None:
        raise RuntimeError("Test mode is active but test context is not ready")


def set_test_state_manager(state_manager: "StateManager | None") -> None:
    """
    Set the active test state manager for the current thread.
    Used internally by the maestro_test fixture.
    """
    _test_context.state_manager = state_manager


def get_test_state_manager() -> "StateManager | None":
    """Get the test state manager of the current thread, or None if not in a test context"""
    return getattr(_test_context, "state_manager", None)


@contextmanager
def test_context(state_manager: "StateManager") -> Generator["StateManager"]:
    """
    Context manager that activates test mode for the current thread.
    All entities referenced from within this context will use the provided state_manager.
    """
    old_state_manager = get_test_state_manager()
    set_test_state_manager(state_manager)
    try:
        yield state_manager
    finally:
        set_test_state_manager(old_state_manager)
