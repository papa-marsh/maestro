# Maestro Testing Framework

A comprehensive pytest-based testing framework for unit testing Maestro automations without affecting your production Home Assistant instance.

## Overview

The Maestro testing framework provides:

- **Complete isolation**: Tests run entirely in-memory with no Redis, PostgreSQL, or Home Assistant connection required
- **Simple API**: Minimal boilerplate with intuitive fixtures and assertion helpers
- **Type safety**: Full type hints throughout
- **Fast execution**: No network calls or external dependencies
- **Easy debugging**: Clear assertion messages and introspection tools

## Quick Start

### Basic Test Structure

```python
from maestro.utils.testing import (
    maestro_test,
    simulate_state_change,
    assert_action_called,
)

def test_my_automation(maestro_test):
    # 1. Set up test entities
    maestro_test.add_entity("switch.space_heater", state="off")

    # 2. Import your automation (registers triggers)
    from scripts.home.office import space_heater

    # 3. Simulate events
    simulate_state_change("switch.space_heater", "off", "on")

    # 4. Make assertions
    assert_action_called("switch.space_heater", "turn_on",
                        hass_client=maestro_test.hass)
```

## Main Components

### The `maestro_test` Fixture

The primary fixture that provides a complete mocked Maestro environment:

```python
def test_example(maestro_test):
    # Access mock components
    maestro_test.hass          # Mock Home Assistant client
    maestro_test.redis         # Mock Redis client
    maestro_test.state         # Mock State Manager
    maestro_test.scheduler     # Mock Job Scheduler

    # Helper methods
    maestro_test.add_entity("switch.fan", state="off")
    maestro_test.get_entity_state("switch.fan")
    maestro_test.get_action_calls()
    maestro_test.get_sent_notifications()
    maestro_test.get_scheduled_jobs()
```

### Trigger Simulators

Simulate Home Assistant events to test your automation logic:

#### State Change Triggers

```python
from maestro.utils.testing import simulate_state_change

simulate_state_change(
    entity_id="switch.space_heater",
    from_state="off",
    to_state="on",
    old_attributes={"friendly_name": "Space Heater"},
    new_attributes={"friendly_name": "Space Heater", "power": 1500}
)
```

#### Event Triggers

```python
from maestro.utils.testing import simulate_event

simulate_event(
    event_type="olivia_asleep",
    data={"duration_seconds": 60}
)
```

#### Notification Action Triggers

```python
from maestro.utils.testing import simulate_notif_action

simulate_notif_action(
    action_name="UNLOCK_DOOR",
    action_data={"door_id": "front_door"}
)
```

### Assertion Helpers

Verify your automation behavior with clear, expressive assertions:

#### Assert Actions Were Called

```python
from maestro.utils.testing import assert_action_called

# Basic usage
assert_action_called("switch.fan", "turn_on",
                    hass_client=maestro_test.hass)

# With parameters
assert_action_called("light.bedroom", "turn_on",
                    hass_client=maestro_test.hass,
                    brightness=255, color_temp=300)

# Check call count
assert_action_called("switch.fan", "toggle",
                    hass_client=maestro_test.hass,
                    times=2)
```

#### Assert Actions Were NOT Called

```python
from maestro.utils.testing import assert_action_not_called

assert_action_not_called("switch.heater", "turn_on",
                        hass_client=maestro_test.hass)
```

#### Assert Notifications Were Sent

```python
from maestro.utils.testing import assert_notification_sent

assert_notification_sent(
    target_entity_id="person.marshall",
    title="Meeting",
    message="Dad's In a Meeting"
)

# Check priority
assert_notification_sent(
    target_entity_id="person.emily",
    priority="time-sensitive"
)
```

#### Assert Jobs Were Scheduled

```python
from maestro.utils.testing import assert_job_scheduled

# By job ID
assert_job_scheduled(
    job_id="office_space_heater_auto_off",
    scheduler=maestro_test.scheduler
)

# By function name and delay
assert_job_scheduled(
    func_name="turn_off_space_heater",
    scheduler=maestro_test.scheduler,
    delay_hours=2
)

# Execute scheduled job to test its logic
job = assert_job_scheduled(job_id="test_job",
                           scheduler=maestro_test.scheduler)
maestro_test.scheduler.execute_job(job.job_id)
```

#### Assert State Changes

```python
from maestro.utils.testing import assert_state_changed, assert_attribute_changed

assert_state_changed("switch.fan", "on",
                     hass_client=maestro_test.hass)

assert_attribute_changed("light.bedroom", "brightness", 255,
                        hass_client=maestro_test.hass)
```

## Complete Examples

### Testing State Change Automations

```python
def test_space_heater_auto_off(maestro_test):
    """Test that space heater auto-off job is scheduled"""
    # Setup
    maestro_test.add_entity("switch.space_heater", state="off")

    # Import automation
    from scripts.home.office.space_heater import space_heater_auto_off

    # Simulate event
    simulate_state_change("switch.space_heater", "off", "on")

    # Assert job scheduled with 2 hour delay
    assert_job_scheduled(
        job_id="office_space_heater_auto_off",
        scheduler=maestro_test.scheduler,
        delay_hours=2
    )
```

### Testing Event-Based Automations

```python
def test_olivia_asleep_sound_machine(maestro_test):
    """Test that sound machine turns on when Olivia is asleep"""
    # Setup
    maestro_test.add_entity("switch.olivias_sound_machine", state="off")

    # Import automation
    from scripts.family.olivia import sound_machine_on

    # Simulate event
    simulate_event(event_type="olivia_asleep")

    # Assert action called
    assert_action_called(
        "switch.olivias_sound_machine",
        "turn_on",
        hass_client=maestro_test.hass
    )
```

### Testing Notification Automations

```python
def test_meeting_notification(maestro_test):
    """Test that meeting notification is sent when Emily is home"""
    # Setup
    maestro_test.add_entity("person.emily", state="home")
    maestro_test.add_entity("maestro.meeting_active", state="off")

    # Import automation
    from scripts.home.office.meetings import toggle_meeting_active

    # Simulate event
    simulate_event(event_type="meeting_active")

    # Assert notification sent
    assert_notification_sent(
        target_entity_id="person.emily",
        title="Dad's In a Meeting",
        priority="time-sensitive"
    )
```

### Testing Multi-Step Workflows

```python
def test_heater_on_off_cancels_job(maestro_test):
    """Test that manually turning off heater cancels auto-off job"""
    # Setup
    maestro_test.add_entity("switch.space_heater", state="off")

    # Import automations
    from scripts.home.office.space_heater import (
        space_heater_auto_off,
        cancel_auto_off_job
    )

    # Turn on heater (schedules job)
    simulate_state_change("switch.space_heater", "off", "on")
    assert_job_scheduled(
        job_id="office_space_heater_auto_off",
        scheduler=maestro_test.scheduler
    )

    # Turn off heater manually (cancels job)
    simulate_state_change("switch.space_heater", "on", "off")
    assert_job_not_scheduled(
        job_id="office_space_heater_auto_off",
        scheduler=maestro_test.scheduler
    )
```

## Advanced Usage

### Custom Entity Attributes

```python
maestro_test.add_entity(
    "sensor.temperature",
    state="72.5",
    attributes={
        "unit_of_measurement": "°F",
        "device_class": "temperature",
        "custom_attr": "custom_value"
    }
)
```

### Accessing Mock Components Directly

```python
# Get all action calls
calls = maestro_test.hass.get_action_calls()

# Filter by domain/action
from maestro.integrations.home_assistant.domain import Domain
light_calls = maestro_test.hass.get_action_calls_for_domain_action(
    Domain.LIGHT, "turn_on"
)

# Clear calls between test steps
maestro_test.clear_action_calls()

# Get all notifications
notifs = maestro_test.get_sent_notifications()

# Get scheduled jobs
jobs = maestro_test.get_scheduled_jobs()
```

### Testing Database Models

For automations that use database models, you can still test the business logic:

```python
def test_location_tracking(maestro_test):
    """Test location tracking logic without database"""
    # Setup entities
    maestro_test.add_entity("person.marshall", state="home")

    # Import and test the function directly
    from scripts.location_tracking.tracking import save_zone_change

    # Create a mock StateChangeEvent
    simulate_state_change("person.marshall", "away", "home")

    # Assert the function executed its logic
    # (Database writes won't persist but you can test side effects)
```

## Running Tests

```bash
# Run all tests
make test

# Run specific test file
make test TEST=maestro/tests/test_example_space_heater.py

# Run specific test method
make test TEST=maestro/tests/test_example_space_heater.py::TestSpaceHeaterAutomation::test_space_heater_schedules_auto_off_when_turned_on
```

## Best Practices

1. **One automation per test method**: Keep tests focused on a single behavior
2. **Clear test names**: Use descriptive names that explain what's being tested
3. **Setup entities first**: Always create entities before importing automations
4. **Test edge cases**: Consider what happens when entities don't exist, states are unexpected, etc.
5. **Use assertion helpers**: They provide better error messages than raw asserts
6. **Clean imports**: Import automation modules inside test functions to isolate trigger registration

## Troubleshooting

### "Entity doesn't exist" errors

Make sure you call `maestro_test.add_entity()` before your automation tries to access it:

```python
# Wrong - entity doesn't exist yet
from scripts.home.office.space_heater import space_heater_auto_off
maestro_test.add_entity("switch.space_heater", state="off")

# Right - entity exists before import
maestro_test.add_entity("switch.space_heater", state="off")
from scripts.home.office.space_heater import space_heater_auto_off
```

### Triggers not firing

Make sure you import the automation module to register its triggers:

```python
# Wrong - triggers not registered
simulate_state_change("switch.fan", "off", "on")

# Right - import first
from scripts.home.office.space_heater import space_heater_auto_off
simulate_state_change("switch.space_heater", "off", "on")
```

### Assertion failures

Use the provided assertion helpers for better error messages:

```python
# Less helpful
assert len(maestro_test.get_action_calls()) > 0

# More helpful
assert_action_called("switch.fan", "turn_on",
                    hass_client=maestro_test.hass)
```

## API Reference

See the docstrings in each module for detailed API documentation:

- `fixtures.py` - Main test fixtures
- `triggers.py` - Event simulation utilities
- `assertions.py` - Assertion helper functions
- `mock_hass_client.py` - Mock Home Assistant client
- `mock_state_manager.py` - Mock state manager
- `mock_scheduler.py` - Mock job scheduler
- `mock_notif.py` - Mock notification system
- `mock_redis.py` - Mock Redis client
