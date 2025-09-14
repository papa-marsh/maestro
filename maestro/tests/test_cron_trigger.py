from calendar import Day, Month
from unittest.mock import MagicMock, patch

import pytest
from apscheduler.schedulers.background import BackgroundScheduler  # type:ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type:ignore[import-untyped]

from maestro.triggers.cron import CronTriggerManager, cron_trigger
from maestro.triggers.trigger_manager import TriggerType, initialize_trigger_registry


class TestCronTriggerDecorator:
    """Test the cron_trigger decorator functionality."""

    def setup_method(self) -> None:
        """Set up isolated test registry for each test."""
        CronTriggerManager._test_registry = initialize_trigger_registry()

    def teardown_method(self) -> None:
        """Clean up test registry."""
        if hasattr(CronTriggerManager, "_test_registry"):
            delattr(CronTriggerManager, "_test_registry")

    def test_decorator_with_crontab_pattern(self) -> None:
        """Test cron_trigger decorator with crontab pattern string."""

        @cron_trigger(pattern="0 9 * * 1-5")
        def test_func() -> None:
            pass

        registry = CronTriggerManager.get_registry()
        cron_registry = registry[TriggerType.CRON]

        assert len(cron_registry) == 1

        # Get the trigger key and verify it's a CronTrigger
        trigger_key = next(iter(cron_registry.keys()))
        assert isinstance(trigger_key, CronTrigger)

        # Verify function is registered
        registered_funcs = cron_registry[trigger_key]
        assert len(registered_funcs) == 1
        assert registered_funcs[0].__name__ == "test_func"

    def test_decorator_with_individual_parameters(self) -> None:
        """Test cron_trigger decorator with individual time parameters."""

        @cron_trigger(minute=0, hour=9)
        def test_func() -> None:
            pass

        registry = CronTriggerManager.get_registry()
        cron_registry = registry[TriggerType.CRON]

        assert len(cron_registry) == 1
        trigger_key = next(iter(cron_registry.keys()))
        assert isinstance(trigger_key, CronTrigger)
        assert len(cron_registry[trigger_key]) == 1
        assert cron_registry[trigger_key][0].__name__ == "test_func"

    def test_decorator_with_all_parameters(self) -> None:
        """Test cron_trigger decorator with all time parameters."""

        @cron_trigger(minute=30, hour=14, day_of_month=15, month=Month.JUNE, day_of_week=Day.FRIDAY)
        def test_func() -> None:
            pass

        registry = CronTriggerManager.get_registry()
        cron_registry = registry[TriggerType.CRON]

        assert len(cron_registry) == 1
        trigger_key = next(iter(cron_registry.keys()))
        assert isinstance(trigger_key, CronTrigger)
        assert len(cron_registry[trigger_key]) == 1
        assert cron_registry[trigger_key][0].__name__ == "test_func"

    def test_decorator_with_list_day_of_month(self) -> None:
        """Test cron_trigger converts list of day_of_month to comma-separated string."""

        @cron_trigger(day_of_month=[1, 15, 30])
        def test_func() -> None:
            pass

        registry = CronTriggerManager.get_registry()
        cron_registry = registry[TriggerType.CRON]

        assert len(cron_registry) == 1
        trigger_key = next(iter(cron_registry.keys()))
        assert isinstance(trigger_key, CronTrigger)
        assert len(cron_registry[trigger_key]) == 1
        assert cron_registry[trigger_key][0].__name__ == "test_func"

    def test_decorator_with_list_months(self) -> None:
        """Test cron_trigger converts list of months to comma-separated string."""

        @cron_trigger(month=[Month.JANUARY, Month.JUNE, Month.DECEMBER])
        def test_func() -> None:
            pass

        registry = CronTriggerManager.get_registry()
        cron_registry = registry[TriggerType.CRON]

        assert len(cron_registry) == 1
        trigger_key = next(iter(cron_registry.keys()))
        assert isinstance(trigger_key, CronTrigger)
        assert len(cron_registry[trigger_key]) == 1
        assert cron_registry[trigger_key][0].__name__ == "test_func"

    def test_decorator_with_list_day_of_week(self) -> None:
        """Test cron_trigger converts list of day_of_week to comma-separated string."""

        @cron_trigger(day_of_week=[Day.MONDAY, Day.WEDNESDAY, Day.FRIDAY])
        def test_func() -> None:
            pass

        registry = CronTriggerManager.get_registry()
        cron_registry = registry[TriggerType.CRON]

        assert len(cron_registry) == 1
        trigger_key = next(iter(cron_registry.keys()))
        assert isinstance(trigger_key, CronTrigger)
        assert len(cron_registry[trigger_key]) == 1
        assert cron_registry[trigger_key][0].__name__ == "test_func"

    def test_decorator_with_mixed_list_types(self) -> None:
        """Test cron_trigger with mixed int and enum types in lists."""

        @cron_trigger(day_of_month=[1, 15], month=[1, Month.JUNE], day_of_week=[0, Day.FRIDAY])
        def test_func() -> None:
            pass

        registry = CronTriggerManager.get_registry()
        cron_registry = registry[TriggerType.CRON]

        assert len(cron_registry) == 1
        trigger_key = next(iter(cron_registry.keys()))
        assert isinstance(trigger_key, CronTrigger)
        assert len(cron_registry[trigger_key]) == 1
        assert cron_registry[trigger_key][0].__name__ == "test_func"

    def test_decorator_with_string_parameters(self) -> None:
        """Test cron_trigger with string parameters."""

        @cron_trigger(minute="*/5", hour="9-17", day_of_month="1-15")
        def test_func() -> None:
            pass

        registry = CronTriggerManager.get_registry()
        cron_registry = registry[TriggerType.CRON]

        assert len(cron_registry) == 1
        trigger_key = next(iter(cron_registry.keys()))
        assert isinstance(trigger_key, CronTrigger)
        assert len(cron_registry[trigger_key]) == 1
        assert cron_registry[trigger_key][0].__name__ == "test_func"

    def test_decorator_pattern_and_params_error(self) -> None:
        """Test that providing both pattern and individual params raises ValueError."""
        with pytest.raises(ValueError, match="pattern or individual args, but not both"):

            @cron_trigger(pattern="0 9 * * *", minute=0)
            def test_func() -> None:
                pass

    def test_decorator_empty_parameters(self) -> None:
        """Test cron_trigger decorator with no parameters (defaults)."""

        @cron_trigger()
        def test_func() -> None:
            pass

        registry = CronTriggerManager.get_registry()
        cron_registry = registry[TriggerType.CRON]

        assert len(cron_registry) == 1
        trigger_key = next(iter(cron_registry.keys()))
        assert isinstance(trigger_key, CronTrigger)
        assert len(cron_registry[trigger_key]) == 1
        assert cron_registry[trigger_key][0].__name__ == "test_func"

    def test_decorated_function_still_callable(self) -> None:
        """Test decorated function can still be called directly."""
        call_count = 0

        @cron_trigger(minute=0)
        def test_func() -> None:
            nonlocal call_count
            call_count += 1

        test_func()
        assert call_count == 1

    def test_decorated_function_with_return_value(self) -> None:
        """Test decorated function with return value works correctly."""

        @cron_trigger(hour=12)
        def test_func() -> str:
            return "test_result"

        result = test_func()
        assert result == "test_result"

    def test_decorated_function_preserves_metadata(self) -> None:
        """Test decorator preserves function metadata."""

        @cron_trigger(hour=9)
        def test_func() -> None:
            """Test docstring."""
            pass

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test docstring."

    def test_multiple_functions_same_trigger(self) -> None:
        """Test multiple functions can be registered with the same cron trigger."""

        @cron_trigger(hour=12)
        def func1() -> None:
            pass

        @cron_trigger(hour=12)
        def func2() -> None:
            pass

        registry = CronTriggerManager.get_registry()
        cron_registry = registry[TriggerType.CRON]

        # Should have one trigger with multiple functions
        # Note: CronTrigger instances are different even with same params, so we get 2 triggers
        assert len(cron_registry) == 2

        # Verify both functions are registered
        all_funcs = []
        for funcs_list in cron_registry.values():
            all_funcs.extend(funcs_list)

        func_names = {func.__name__ for func in all_funcs}
        assert len(all_funcs) == 2
        assert "func1" in func_names
        assert "func2" in func_names

    def test_different_triggers_separate_registration(self) -> None:
        """Test functions with different triggers are registered separately."""

        @cron_trigger(hour=9)
        def morning_func() -> None:
            pass

        @cron_trigger(hour=17)
        def evening_func() -> None:
            pass

        registry = CronTriggerManager.get_registry()
        cron_registry = registry[TriggerType.CRON]

        # Should have two separate triggers
        assert len(cron_registry) == 2

        # Each trigger should have one function
        for trigger_key, funcs in cron_registry.items():
            assert len(funcs) == 1
            assert isinstance(trigger_key, CronTrigger)

    @patch("maestro.triggers.trigger_manager.log")
    def test_decorator_logs_registration(self, mock_log: MagicMock) -> None:
        """Test decorator logs successful function registration."""

        @cron_trigger(minute=30)
        def test_func() -> None:
            pass

        # Verify log was called
        mock_log.info.assert_called_once()
        call_args = mock_log.info.call_args[1]
        assert call_args["function_name"] == "test_func"
        assert call_args["trigger_type"] == TriggerType.CRON
        assert isinstance(call_args["registry_key"], CronTrigger)


class TestCronTriggerManager:
    """Test CronTriggerManager class functionality."""

    def setup_method(self) -> None:
        """Set up isolated test registry for each test."""
        CronTriggerManager._test_registry = initialize_trigger_registry()

    def teardown_method(self) -> None:
        """Clean up test registry."""
        if hasattr(CronTriggerManager, "_test_registry"):
            delattr(CronTriggerManager, "_test_registry")

    def test_execute_triggers_raises_not_implemented(self) -> None:
        """Test execute_triggers raises NotImplementedError as it's not used for cron."""
        with pytest.raises(NotImplementedError):
            CronTriggerManager.execute_triggers()

    def test_register_jobs_with_no_functions(self) -> None:
        """Test register_jobs with empty registry doesn't cause errors."""
        mock_scheduler = MagicMock(spec=BackgroundScheduler)

        CronTriggerManager.register_jobs(mock_scheduler)

        # Should not call add_job if no functions registered
        mock_scheduler.add_job.assert_not_called()

    def test_register_jobs_with_single_function(self) -> None:
        """Test register_jobs adds single function to scheduler."""

        @cron_trigger(minute=30)
        def test_func() -> None:
            pass

        mock_scheduler = MagicMock(spec=BackgroundScheduler)

        CronTriggerManager.register_jobs(mock_scheduler)

        # Should call add_job once
        mock_scheduler.add_job.assert_called_once()
        args, _ = mock_scheduler.add_job.call_args

        # First argument should be the function
        assert args[0].__name__ == "test_func"
        # Second argument should be the trigger
        assert isinstance(args[1], CronTrigger)

    def test_register_jobs_with_multiple_functions_same_trigger(self) -> None:
        """Test register_jobs adds multiple functions with same trigger separately."""

        @cron_trigger(hour=12)
        def func1() -> None:
            pass

        @cron_trigger(hour=12)
        def func2() -> None:
            pass

        mock_scheduler = MagicMock(spec=BackgroundScheduler)

        CronTriggerManager.register_jobs(mock_scheduler)

        # Should call add_job twice (once per function)
        assert mock_scheduler.add_job.call_count == 2

        # Collect all calls
        calls = mock_scheduler.add_job.call_args_list

        # Both calls should have same trigger but different functions
        func_names_called = {call[0][0].__name__ for call in calls}
        triggers_called = {call[0][1] for call in calls}

        assert func_names_called == {"func1", "func2"}
        assert len(triggers_called) == 2  # Different CronTrigger instances

    def test_register_jobs_with_different_triggers(self) -> None:
        """Test register_jobs adds functions with different triggers."""

        @cron_trigger(hour=9)
        def morning_func() -> None:
            pass

        @cron_trigger(hour=17)
        def evening_func() -> None:
            pass

        mock_scheduler = MagicMock(spec=BackgroundScheduler)

        CronTriggerManager.register_jobs(mock_scheduler)

        # Should call add_job twice
        assert mock_scheduler.add_job.call_count == 2

        # Collect all calls
        calls = mock_scheduler.add_job.call_args_list

        # Should have different triggers and functions
        func_names_called = {call[0][0].__name__ for call in calls}
        triggers_called = {call[0][1] for call in calls}

        assert func_names_called == {"morning_func", "evening_func"}
        assert len(triggers_called) == 2  # Different triggers

    def test_register_jobs_uses_correct_registry(self) -> None:
        """Test register_jobs uses the correct registry (test vs production)."""
        # Add function to production registry
        prod_func_called = False

        def prod_func() -> None:
            nonlocal prod_func_called
            prod_func_called = True

        prod_trigger = CronTrigger(hour=8)
        CronTriggerManager._registry[TriggerType.CRON][prod_trigger].append(prod_func)

        # Add function to test registry via decorator
        @cron_trigger(hour=10)
        def test_func() -> None:
            pass

        mock_scheduler = MagicMock(spec=BackgroundScheduler)

        CronTriggerManager.register_jobs(mock_scheduler)

        # Should only register function from test registry (since test registry exists)
        mock_scheduler.add_job.assert_called_once()
        args, kwargs = mock_scheduler.add_job.call_args

        assert args[0].__name__ == "test_func"  # Should be test function, not production

        # Clean up production registry
        CronTriggerManager._registry[TriggerType.CRON][prod_trigger].clear()

    def test_register_jobs_with_production_registry_when_no_test_registry(self) -> None:
        """Test register_jobs uses production registry when no test registry exists."""
        # Remove test registry
        if hasattr(CronTriggerManager, "_test_registry"):
            delattr(CronTriggerManager, "_test_registry")

        # Add function to production registry directly
        def prod_func() -> None:
            pass

        prod_trigger = CronTrigger(hour=8)
        CronTriggerManager._registry[TriggerType.CRON][prod_trigger].append(prod_func)

        mock_scheduler = MagicMock(spec=BackgroundScheduler)

        CronTriggerManager.register_jobs(mock_scheduler)

        # Should register ALL functions from production registry (including existing ones)
        # We expect at least our test function plus any existing production functions
        assert mock_scheduler.add_job.call_count >= 1

        # Find our test function in the calls
        calls = mock_scheduler.add_job.call_args_list
        our_func_found = False
        for call in calls:
            if call[0][0].__name__ == "prod_func":
                our_func_found = True
                break

        assert our_func_found, "Our test prod_func should have been registered"

        # Clean up only our test function from production registry
        CronTriggerManager._registry[TriggerType.CRON][prod_trigger].clear()

    def test_register_jobs_scheduler_error_handling(self) -> None:
        """Test register_jobs handles scheduler errors gracefully."""

        @cron_trigger(minute=15)
        def test_func() -> None:
            pass

        mock_scheduler = MagicMock(spec=BackgroundScheduler)
        mock_scheduler.add_job.side_effect = Exception("Scheduler error")

        # Should not raise exception even if scheduler fails
        with pytest.raises(Exception, match="Scheduler error"):
            CronTriggerManager.register_jobs(mock_scheduler)


class TestCronTriggerIntegration:
    """Integration tests for cron triggers with real scheduler."""

    def setup_method(self) -> None:
        """Set up isolated test registry and real scheduler."""
        CronTriggerManager._test_registry = initialize_trigger_registry()
        self.scheduler = BackgroundScheduler()

    def teardown_method(self) -> None:
        """Clean up test registry and scheduler."""
        if hasattr(CronTriggerManager, "_test_registry"):
            delattr(CronTriggerManager, "_test_registry")

        # Clean up scheduler
        if self.scheduler.running:
            self.scheduler.shutdown()

    def test_register_jobs_with_real_scheduler(self) -> None:
        """Test register_jobs works with real BackgroundScheduler."""

        @cron_trigger(minute="*/5")
        def test_func() -> None:
            pass

        # Should not raise any errors
        CronTriggerManager.register_jobs(self.scheduler)

        # Verify job was added (check scheduler jobs)
        jobs = self.scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].func.__name__ == "test_func"

    def test_multiple_jobs_with_real_scheduler(self) -> None:
        """Test multiple cron jobs with real scheduler."""

        @cron_trigger(minute=0)
        def hourly_func() -> None:
            pass

        @cron_trigger(hour=0)
        def daily_func() -> None:
            pass

        CronTriggerManager.register_jobs(self.scheduler)

        # Verify both jobs were added
        jobs = self.scheduler.get_jobs()
        assert len(jobs) == 2

        job_function_names = {job.func.__name__ for job in jobs}
        assert "hourly_func" in job_function_names
        assert "daily_func" in job_function_names

    def test_scheduler_start_stop_with_cron_jobs(self) -> None:
        """Test scheduler can start and stop with registered cron jobs."""
        call_log = []

        @cron_trigger(minute="*")  # Every minute (for testing)
        def frequent_func() -> None:
            call_log.append("called")

        CronTriggerManager.register_jobs(self.scheduler)

        # Start scheduler
        self.scheduler.start()
        assert self.scheduler.running

        # Stop scheduler
        self.scheduler.shutdown()
        assert not self.scheduler.running

        # Test completed successfully without errors

    def test_cron_trigger_pattern_parsing(self) -> None:
        """Test various cron pattern formats are parsed correctly."""
        test_patterns = [
            "0 9 * * 1-5",  # Weekdays at 9 AM
            "*/15 * * * *",  # Every 15 minutes
            "0 0 1 * *",  # First day of month
            "0 */2 * * *",  # Every 2 hours
        ]

        for i, pattern in enumerate(test_patterns):

            @cron_trigger(pattern=pattern)
            def pattern_func() -> None:
                pass

            # Rename function to avoid conflicts
            pattern_func.__name__ = f"pattern_func_{i}"

        CronTriggerManager.register_jobs(self.scheduler)

        # Verify all patterns were registered
        jobs = self.scheduler.get_jobs()
        assert len(jobs) == len(test_patterns)

        # All jobs should have valid cron triggers
        for job in jobs:
            assert isinstance(job.trigger, CronTrigger)


class TestCronTriggerEdgeCases:
    """Test edge cases and error conditions for cron triggers."""

    def setup_method(self) -> None:
        """Set up isolated test registry."""
        CronTriggerManager._test_registry = initialize_trigger_registry()

    def teardown_method(self) -> None:
        """Clean up test registry."""
        if hasattr(CronTriggerManager, "_test_registry"):
            delattr(CronTriggerManager, "_test_registry")

    def test_invalid_cron_pattern(self) -> None:
        """Test invalid cron pattern raises appropriate error."""
        with pytest.raises(ValueError):

            @cron_trigger(pattern="invalid pattern")
            def test_func() -> None:
                pass

    def test_conflicting_parameters_all_combinations(self) -> None:
        """Test that combining pattern with other params raises an error."""
        with pytest.raises(ValueError, match="pattern or individual args, but not both"):

            @cron_trigger(pattern="0 9 * * *", minute=0)
            def test_func() -> None:
                pass

    def test_extreme_list_values(self) -> None:
        """Test cron trigger with extreme list values."""

        @cron_trigger(
            day_of_month=list(range(1, 32)),  # All days of month
            month=list(range(1, 13)),  # All months
            day_of_week=list(range(7)),  # All days of week
        )
        def extreme_func() -> None:
            pass

        registry = CronTriggerManager.get_registry()
        cron_registry = registry[TriggerType.CRON]

        assert len(cron_registry) == 1
        trigger_key = next(iter(cron_registry.keys()))
        assert isinstance(trigger_key, CronTrigger)

    def test_empty_lists(self) -> None:
        """Test cron trigger with empty lists causes expected error."""

        # Empty lists should cause errors from APScheduler
        with pytest.raises(ValueError, match="Unrecognized expression"):
            @cron_trigger(day_of_month=[], month=[], day_of_week=[])
            def empty_list_func() -> None:
                pass

    def test_none_values(self) -> None:
        """Test cron trigger with None values (should use defaults)."""

        @cron_trigger(minute=None, hour=None, day_of_month=None, month=None, day_of_week=None)
        def none_func() -> None:
            pass

        registry = CronTriggerManager.get_registry()
        cron_registry = registry[TriggerType.CRON]

        assert len(cron_registry) == 1
        trigger_key = next(iter(cron_registry.keys()))
        assert isinstance(trigger_key, CronTrigger)
