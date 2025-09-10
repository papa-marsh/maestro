# Maestro

**Write your Home Assistant automations in Python.** 

Maestro bridges Home Assistant with Python automation scripts, giving you real-time state synchronization, typed entity interfaces, and decorator-based triggers - all while keeping your Home Assistant setup unchanged.

## What is Maestro?

Instead of writing complex YAML automations, write clean Python:

```python
from maestro import state_change_trigger, EntityId

@state_change_trigger("switch.living_room_light")
def bedtime_routine(state_change):
    if state_change.new_state == "off" and is_bedtime():
        # Turn off all lights, lock doors, adjust thermostat
        turn_off_all_lights()
        lock_all_doors()
        set_sleep_temperature()
```

## Quick Start

### 1. Deploy Maestro

```bash
git clone https://github.com/your-repo/maestro.git
cd maestro
cp .env.example .env
# Edit .env with your Home Assistant URL and access token
make build
docker-compose up -d
```

### 2. Connect Home Assistant

Add to your Home Assistant `configuration.yaml`:

```yaml
rest_command:
  send_to_maestro:
    url: "http://your-maestro-server/events/state-changed"
    method: POST
    headers:
      Content-Type: "application/json"
    payload: >
      {
        "timestamp": "{{ now().isoformat() }}",
        "time_fired": "{{ time_fired }}",
        "event_type": "{{ event_type }}",
        "entity_id": "{{ entity_id }}",
        "old_state": "{{ old_state }}",
        "new_state": "{{ new_state }}",
        "old_attributes": {{ old_attributes | tojson }},
        "new_attributes": {{ new_attributes | tojson }}
      }
```

Add to your `automations.yaml`:

```yaml
- alias: "Send state changes to Maestro"
  trigger:
    - platform: event
      event_type: state_changed
  condition:
    - condition: template
      value_template: "{{ not trigger.event.data.entity_id.startswith('automation.') }}"
  action:
    - service: rest_command.send_to_maestro
      data:
        time_fired: "{{ trigger.event.time_fired }}"
        event_type: "{{ trigger.event.event_type }}"
        entity_id: "{{ trigger.event.data.entity_id }}"
        old_state: "{{ trigger.event.data.old_state.state if trigger.event.data.old_state else none }}"
        new_state: "{{ trigger.event.data.new_state.state if trigger.event.data.new_state else none }}"
        old_attributes: "{{ trigger.event.data.old_state.attributes if trigger.event.data.old_state else {} }}"
        new_attributes: "{{ trigger.event.data.new_state.attributes if trigger.event.data.new_state else {} }}"
  mode: parallel
```

### 3. Write Your Automations

Create your automation scripts in the `scripts/` directory (see [scripts/README.md](scripts/README.md) for details):

```python
from maestro import state_change_trigger, Switch, Climate

@state_change_trigger("binary_sensor.front_door")
def front_door_opened(state_change):
    if state_change.new_state == "on":  # Door opened
        # Turn on entryway light
        entryway_light = Switch("switch.entryway")
        entryway_light.turn_on()

@state_change_trigger("sensor.outdoor_temperature") 
def adjust_thermostat(state_change):
    temp = float(state_change.new_state)
    thermostat = Climate("climate.main")
    
    if temp > 75:
        thermostat.set_temperature(72)
    elif temp < 60:
        thermostat.set_temperature(70)
```

## Key Features

- **🎯 Event-driven** - React to Home Assistant state changes in real-time
- **🔒 Type-safe** - Full typing support with intelligent parameter injection
- **⚡ High-performance** - Redis caching minimizes Home Assistant API calls  
- **🏗️ Object-oriented** - `switch.turn_on()` instead of service calls
- **🧪 Testable** - Isolated test registry system for reliable testing
- **📦 Extensible** - Clean architecture for adding new trigger types

## Environment Setup

Copy `.env.example` to `.env` and configure:

```bash
HOME_ASSISTANT_URL=http://your-hass-ip:8123
HOME_ASSISTANT_TOKEN=your-long-lived-access-token
REDIS_HOST=redis
REDIS_PORT=6379
NGINX_TOKEN=your-secure-token
```

## Project Structure

- **`/`** - This README and deployment configuration
- **`maestro/`** - Core middleware system ([README](maestro/README.md))
- **`scripts/`** - Your automation scripts ([README](scripts/README.md))

## Requirements

- Python 3.12+
- Docker & Docker Compose
- Home Assistant with REST API access
- Redis (included in docker-compose)

## Contributing

Maestro provides the foundation for Python-based Home Assistant automation. The core system handles entity management, caching, webhooks, and triggers - ready for your custom automation logic.

See [maestro/README.md](maestro/README.md) for development and contribution guidelines.
