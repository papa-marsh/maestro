from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from maestro.integrations.state_manager import StateManager
    from maestro.testing.mocks import MockJobScheduler


# Global test context
_test_state_manager: "StateManager | None" = None
_test_job_scheduler: "MockJobScheduler | None" = None


def get_test_job_scheduler() -> "MockJobScheduler":
    """Lazily fetch the global test mock job scheduler"""
    global _test_job_scheduler

    if _test_job_scheduler is None:
        from maestro.testing.mocks import MockJobScheduler

        _test_job_scheduler = MockJobScheduler()

    return _test_job_scheduler


def get_test_state_manager() -> "StateManager":
    """Lazily fetch the global test mock state manager"""
    global _test_state_manager

    if _test_state_manager is None:
        from maestro.integrations.state_manager import StateManager
        from maestro.testing.mocks import MockHomeAssistantClient, MockRedisClient

        _test_state_manager = StateManager(
            hass_client=MockHomeAssistantClient(),
            redis_client=MockRedisClient(),
        )

    return _test_state_manager


def reset_test_context() -> None:
    global _test_state_manager, _test_job_scheduler
    _test_state_manager = None
    _test_job_scheduler = None
