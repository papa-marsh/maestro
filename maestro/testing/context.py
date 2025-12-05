import threading
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from maestro.utils.exceptions import TestFrameworkError

if TYPE_CHECKING:
    from maestro.integrations.state_manager import StateManager
    from maestro.testing.mocks import MockJobScheduler


_test_context = threading.local()


def set_test_job_scheduler(job_scheduler: "MockJobScheduler | None") -> None:
    """Set the active test mock scheduler for the current test thread."""
    _test_context.job_scheduler = job_scheduler


def get_test_job_scheduler() -> "MockJobScheduler":
    """Get the test mock scheduler of the current thread"""
    job_scheduler: MockJobScheduler | None = getattr(_test_context, "job_scheduler", None)

    if job_scheduler is None:
        raise TestFrameworkError("Couldn't find test job scheduler. Is the test context active?")

    return job_scheduler


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
def test_context(
    state_manager: "StateManager",
    job_scheduler: "MockJobScheduler",
) -> Generator["StateManager"]:
    """
    Context manager that activates test mode for the current thread.
    All state manager instances will use the test context's mocked state_manager and job_scheduler.
    """
    set_test_state_manager(state_manager)
    set_test_job_scheduler(job_scheduler)
    try:
        yield state_manager
    finally:
        set_test_state_manager(None)
        set_test_job_scheduler(None)
