# Maestro

A Python middleware Flask application that bridges Home Assistant with custom automation logic engines. Maestro provides a typed, object-oriented interface for Home Assistant entities with intelligent caching and real-time state synchronization.

## Architecture

- **Flask API Server** - Receives Home Assistant state change webhooks
- **Redis Cache Layer** - High-performance entity state storage with type preservation
- **Home Assistant Client** - Full REST API integration for bidirectional communication
- **Entity Abstraction** - Typed Python classes for Home Assistant entities

## Quick Start

1. **Configure Environment**

   ```bash
   cp .env.example .env
   # Edit .env with your Home Assistant URL and long-lived access token
   ```

2. **Start Services**

   ```bash
   docker-compose up -d
   ```

3. **Configure Home Assistant REST Command Service**
   Give Home Assistant a command that can send state changes to Maestro:

   ```yaml
   # config.yaml

   rest_command:
   send_state_change_to_maestro:
     url: !secret maestro_state_changed_url
     method: POST
     headers:
       Content-Type: "application/json"
       X-Auth-Token: !secret maestro_token
     payload: >
       {
          "timestamp": {{ now().isoformat()| tojson }},
          "time_fired": {{ time_fired | tojson }},
          "event_type": {{ event_type | tojson }},
          "entity_id": {{ entity_id | tojson }},
          "old_state": {{ old_state | tojson }},
          "new_state": {{ new_state | tojson }},
          "old_attributes": {{ old_attributes }},
          "new_attributes": {{ new_attributes }}
       }
   ```

4. **Configure Home Assistant Automation**
   Create an automation that will trigger the REST command on state changes:

   ```yaml
   # automations.yaml

   - id: "1234567890123"
     alias: Maestro Send State Changed
     description: ""
     triggers:
        - trigger: event
           event_type: state_changed
           context: {}
     conditions:
        - condition: not
           conditions:
           - condition: template
              value_template: "{{ trigger.event.data.entity_id.startswith('automation.') }}"
     actions:
        - action: rest_command.send_to_maestro
           metadata: {}
           data:
           time_fired: "{{ trigger.event.time_fired }}"
           event_type: "{{ trigger.event.event_type }}"
           entity_id: "{{ trigger.event.data.entity_id }}"
           old_state: "{{ trigger.event.data.old_state.state }}"
           new_state: "{{ trigger.event.data.new_state.state }}"
           old_attributes: "{{ trigger.event.data.old_state.attributes | tojson }}"
           new_attributes: "{{ trigger.event.data.new_state.attributes | tojson }}"
     mode: parallel
   ```

## Usage

### Entity Management

```python
from maestro.entities.switch import Switch
from maestro.entities.climate import Climate

# Work with entities using typed interfaces
living_room_light = Switch("switch.living_room_light")
living_room_light.turn_on()

thermostat = Climate("climate.living_room")
thermostat.set_temperature(72)
print(f"Current temp: {thermostat.current_temperature}°F")
```

## API Endpoints

- `GET /` - Health check
- `POST /events/state-changed` - Webhook for Home Assistant state changes
- `POST /payload-testing` - Development endpoint for testing payloads

## Development

### Requirements

- Python 3.12+
- Docker & Docker Compose
- Home Assistant with REST API access

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Type checking
mypy maestro/

# Code formatting
ruff check maestro/
```

### Environment Variables

```bash
HOME_ASSISTANT_URL=http://your-hass-ip:8123
HOME_ASSISTANT_TOKEN=your-long-lived-access-token
REDIS_HOST=redis
REDIS_PORT=6379
NGINX_TOKEN=your-secure-token
```

## Entity Types

Currently supported Home Assistant domains:

- `switch` - Binary switches with on/off/toggle actions
- `climate` - HVAC systems with temperature and fan controls
- `calendar` - Calendar entities (basic support)

## Cache Architecture

Maestro intelligently caches entity states and attributes in Redis:

- **Type Preservation** - Maintains Python types (int, float, dict, etc.)
- **Selective Caching** - Ignores UI-only attributes like icons
- **30-Day TTL** - Automatic expiration prevents stale data
- **Real-time Updates** - Webhook integration keeps cache current

## Contributing

This project serves as middleware for Python-based Home Assistant automation engines. The current implementation provides the foundation - entity management, caching, and HA integration - ready for your custom automation logic.
