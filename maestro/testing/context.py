import threading
from collections.abc import Generator
from contextlib import contextmanager

from maestro.integrations.state_manager import StateManager

# Thread-local storage for test context
_test_context = threading.local()


def set_test_state_manager(state_manager: StateManager | None) -> None:
    """
    Set the active test state manager for the current thread.
    Used internally by the maestro_test fixture.
    """
    _test_context.state_manager = state_manager


def get_test_state_manager() -> StateManager | None:
    """
    Get the active test state manager for the current thread, if any.
    Returns None if not in a test context.
    """
    return getattr(_test_context, "state_manager", None)


@contextmanager
def test_context(state_manager: StateManager) -> Generator[StateManager]:
    """
    Context manager that activates test mode for the current thread.
    All entities created within this context will automatically use the provided state_manager.

    Usage:
        with test_context(my_state_manager):
            # All entities will use my_state_manager
            entity.turn_on()
    """
    old_state_manager = get_test_state_manager()
    set_test_state_manager(state_manager)
    try:
        yield state_manager
    finally:
        set_test_state_manager(old_state_manager)
