# Maestro Automation Scripts

Write your Home Assistant automation logic here using Python instead of YAML. This directory is where you'll create reactive automation scripts that respond to Home Assistant state changes in real-time.

## Getting Started

### Your First Automation

Create a new Python file (e.g., `lighting.py`) in this directory:

```python
from maestro.domains import Switch
from maestro.integrations import StateChangeEvent
from maestro.triggers import state_change_trigger

@state_change_trigger("binary_sensor.front_door")
def front_door_opened(state_change: StateChangeEvent) -> None:
    if state_change.new_state == "on":
        entryway_light = Switch("switch.entryway")
        entryway_light.turn_on()
```

### How It Works

1. **Import what you need** from `maestro`
2. **Decorate functions** with `@state_change_trigger("entity.id")`
3. **Write your logic** - your function gets called automatically when the entity changes
4. **Access the state change** via the `state_change` parameter (optional)

## Available Imports

```python
# Core trigger system
from maestro.triggers import state_change_trigger

# Entity domain types
from maestro.domains import Switch, Climate, ...

# Home Assistant & middleware types
from maestro.integrations import EntityId, StateChangeEvent

# State management (advanced usage)
from maestro.integrations import StateManager
```

## Entity Class Examples

### Switch

Binary switches with on/off/toggle functionality:

```python
from maestro import Switch

# Create switch instance
light = Switch("switch.living_room_light")

# Control the switch
light.turn_on()
light.turn_off()
light.toggle()

# Check current state
if light.is_on():
    print("Light is on")
```

### Climate

HVAC systems with temperature and fan controls:

```python
from maestro import Climate

thermostat = Climate("climate.main_thermostat")

# Temperature control
thermostat.set_temperature(72)
print(f"Current temp: {thermostat.current_temperature}°F")
print(f"Target temp: {thermostat.target_temperature}°F")

# Mode control
thermostat.set_hvac_mode("heat")  # heat, cool, auto, off
thermostat.set_fan_mode("auto")   # auto, on, off
```

## Automation Patterns

### Conditional Logic

```python
from maestro import state_change_trigger, Switch
from datetime import datetime

@state_change_trigger("binary_sensor.motion_living_room")
def motion_lighting(state_change):
    if state_change.new_state == "on":
        current_hour = datetime.now().hour

        light = Switch("switch.living_room_light")
        if 6 <= current_hour <= 22:  # Daytime
            light.turn_on()
        elif 22 < current_hour or current_hour < 6:  # Night
            # Turn on at lower brightness (if supported)
            light.turn_on()
```

### Multiple Entities

```python
@state_change_trigger("input_boolean.movie_mode")
def movie_mode(state_change):
    if state_change.new_state == "on":
        # Turn off all lights
        living_room_light = Switch("switch.living_room_light")
        kitchen_light = Switch("switch.kitchen_light")
        bedroom_light = Switch("switch.bedroom_light")

        living_room_light.turn_off()
        kitchen_light.turn_off()
        bedroom_light.turn_off()

        # Adjust thermostat for comfort
        thermostat = Climate("climate.main")
        thermostat.set_temperature(70)
```

### Multiple Triggers for Same Function

```python
# Multiple entities can trigger the same function
@state_change_trigger("binary_sensor.door_front")
@state_change_trigger("binary_sensor.door_back")
@state_change_trigger("binary_sensor.door_garage")
def door_opened(state_change):
    if state_change.new_state == "on":
        # Any door opened - turn on security lights
        security_light = Switch("switch.security_lights")
        security_light.turn_on()
        print(f"Door {state_change.entity_id} opened!")
```

### Temperature-Based Automation

```python
@state_change_trigger("sensor.outdoor_temperature")
def temperature_automation(state_change):
    outdoor_temp = float(state_change.new_state)
    thermostat = Climate("climate.main")

    if outdoor_temp > 80:
        thermostat.set_temperature(72)  # Cool down
        thermostat.set_hvac_mode("cool")
    elif outdoor_temp < 50:
        thermostat.set_temperature(70)  # Warm up
        thermostat.set_hvac_mode("heat")
    else:
        thermostat.set_hvac_mode("auto")  # Let it decide
```

## Advanced Usage

### Using StateChangeEvent Details

The `state_change` parameter contains rich information:

```python
@state_change_trigger("sensor.energy_meter")
def energy_monitoring(state_change):
    print(f"Entity: {state_change.entity_id}")
    print(f"Old state: {state_change.old_state}")
    print(f"New state: {state_change.new_state}")
    print(f"Timestamp: {state_change.timestamp}")
    print(f"Time fired: {state_change.time_fired}")
    print(f"Old attributes: {state_change.old_attributes}")
    print(f"New attributes: {state_change.new_attributes}")
```

### Functions Without Parameters

If you don't need state change details, omit the parameter:

```python
@state_change_trigger("button.doorbell")
def doorbell_pressed():  # No parameters
    # Play doorbell sound, send notification, etc.
    print("Doorbell pressed!")
```

### Using EntityId Objects

For better organization and reusability:

```python
from maestro import EntityId, state_change_trigger, Switch

# Define your entities
LIVING_ROOM_LIGHT = EntityId("switch.living_room_light")
FRONT_DOOR = EntityId("binary_sensor.front_door")

@state_change_trigger(FRONT_DOOR)
def front_door_handler(state_change):
    if state_change.new_state == "on":
        light = Switch(LIVING_ROOM_LIGHT)
        light.turn_on()
```

## File Organization

### Recommended Structure

```
scripts/
├── __init__.py
├── README.md           # This file
├── lighting.py         # Light-related automations
├── climate.py          # Temperature/HVAC automations
├── security.py         # Door/window/motion automations
├── scenes.py           # Scene-based automations
└── utils.py            # Shared helper functions
```

### Example: Shared Utilities

Create `utils.py` for common functions:

```python
# utils.py
from maestro import Switch
from datetime import datetime

def is_nighttime() -> bool:
    hour = datetime.now().hour
    return hour < 7 or hour > 22

def turn_off_all_lights():
    lights = [
        "switch.living_room_light",
        "switch.kitchen_light",
        "switch.bedroom_light"
    ]
    for light_id in lights:
        Switch(light_id).turn_off()
```

Then use in your automations:

```python
# lighting.py
from maestro import state_change_trigger
from .utils import is_nighttime, turn_off_all_lights

@state_change_trigger("input_boolean.bedtime_mode")
def bedtime_routine(state_change):
    if state_change.new_state == "on":
        turn_off_all_lights()
```

## Testing Your Scripts

Since your scripts are just Python functions, you can test them:

```python
# test_lighting.py
from maestro.integrations.home_assistant.types import EntityId, StateChangeEvent
from maestro.utils.dates import utc_now
from lighting import front_door_automation

def test_front_door_automation():
    # Create a mock state change
    state_change = StateChangeEvent(
        timestamp=utc_now(),
        time_fired=utc_now(),
        event_type="state_changed",
        entity_id=EntityId("binary_sensor.front_door"),
        old_state="off",
        new_state="on",
        old_attributes={},
        new_attributes={}
    )

    # Test your function
    front_door_automation(state_change)
    # Add assertions as needed
```

Run your script tests using the project's test system:

```bash
# Run all tests (including your script tests)
make test

# Run just your script tests
make test TEST=scripts/test_lighting.py
```

## Troubleshooting

### My automation isn't triggering

- Check that Maestro is receiving webhooks from Home Assistant
- Verify the entity ID matches exactly (case-sensitive)
- Check Maestro logs: `docker-compose logs maestro`

### Entity not found errors

- Ensure the entity exists in Home Assistant
- Check entity ID spelling and format
- Verify Home Assistant API token has access

### Debug with interactive shell

Use the Flask shell to test your entity connections:

```bash
# Open interactive shell with pre-loaded Maestro imports
make shell

# Then in the shell:
>>> light = Switch("switch.living_room_light")
>>> light.turn_on()
```

## Getting Help

- Check Maestro logs: `docker-compose logs maestro`
- Use interactive debugging: `make shell` or `make bash`
- Verify Home Assistant connectivity: Check `/` endpoint for health
- Review the [main README](../README.md) for setup issues
- See [maestro/README.md](../maestro/README.md) for development details

## What's Next?

As Maestro evolves, more entity types and trigger types will be added. The patterns you learn here will extend naturally to new capabilities like time-based triggers, complex event patterns, and additional Home Assistant integrations.
