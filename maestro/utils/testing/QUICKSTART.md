# Maestro Testing Quick Start

Get started testing your Maestro automations in 5 minutes.

## Step 1: Create a Test File

Create a test file in your scripts directory or `maestro/tests/`:

```python
# scripts/home/office/test_space_heater.py
from maestro.utils.testing import (
    maestro_test,
    simulate_state_change,
    assert_action_called,
    assert_job_scheduled,
)
```

## Step 2: Write Your First Test

```python
def test_space_heater_auto_off(maestro_test):
    # 1. Add entities your automation needs
    maestro_test.add_entity("switch.space_heater", state="off")

    # 2. Import your automation
    from scripts.home.office.space_heater import space_heater_auto_off

    # 3. Simulate an event
    simulate_state_change(
        entity_id="switch.space_heater",
        from_state="off",
        to_state="on"
    )

    # 4. Assert expected behavior
    assert_job_scheduled(
        job_id="office_space_heater_auto_off",
        scheduler=maestro_test.scheduler,
        delay_hours=2
    )
```

## Step 3: Run Your Test

```bash
make test TEST=scripts/home/office/test_space_heater.py
```

## Common Patterns

### Testing State Change Triggers

```python
def test_my_state_trigger(maestro_test):
    maestro_test.add_entity("switch.my_device", state="off")
    from scripts.my_automation import my_function

    simulate_state_change("switch.my_device", "off", "on")

    assert_action_called("light.indicator", "turn_on",
                        hass_client=maestro_test.hass)
```

### Testing Event Triggers

```python
def test_my_event_trigger(maestro_test):
    maestro_test.add_entity("switch.my_device", state="off")
    from scripts.my_automation import my_function

    simulate_event(event_type="my_custom_event")

    assert_action_called("switch.my_device", "turn_on",
                        hass_client=maestro_test.hass)
```

### Testing Notifications

```python
def test_notification_sent(maestro_test):
    maestro_test.add_entity("person.john", state="home")
    from scripts.my_automation import my_function

    simulate_state_change("binary_sensor.door", "off", "on")

    assert_notification_sent(
        target_entity_id="person.john",
        title="Alert",
        message="Door opened"
    )
```

### Testing Scheduled Jobs

```python
def test_job_scheduled(maestro_test):
    maestro_test.add_entity("switch.device", state="on")
    from scripts.my_automation import my_function

    simulate_state_change("switch.device", "off", "on")

    job = assert_job_scheduled(
        job_id="my_job_id",
        scheduler=maestro_test.scheduler,
        delay_hours=1
    )

    # Test the job's logic by executing it
    maestro_test.scheduler.execute_job(job.job_id)
    assert_action_called("switch.device", "turn_off",
                        hass_client=maestro_test.hass)
```

## Tips

1. **Always add entities before importing automations**
2. **Import automations inside test functions** (not at module level)
3. **Use clear, descriptive test names**
4. **Test one behavior per test function**
5. **Use assertion helpers for better error messages**

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check out [test_example_space_heater.py](../../tests/test_example_space_heater.py) for complete examples
- Run `make test` to see the framework in action

## Need Help?

Common issues and solutions:

**"Entity doesn't exist"**: Add the entity before importing your automation
```python
maestro_test.add_entity("switch.my_device", state="off")  # Do this first
from scripts.my_automation import my_function              # Then import
```

**"No triggers fired"**: Make sure you imported the automation module
```python
from scripts.my_automation import my_function  # This registers triggers
simulate_state_change(...)                      # Now this will work
```

**"Can't find maestro_test"**: Make sure you have the `conftest.py` at the repo root
