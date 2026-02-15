# Maestro

**Strongly-typed Python automations for Home Assistant**

Maestro is a framework that lets you write Home Assistant automations in Python with full type safety, IDE autocomplete, and a clean decorator-based API. Instead of YAML configurations, write real Python code with access to your entities as typed objects.

**Note:** A ~~picture~~ _repo_ is worth a thousand words. Check out some real world examples here: https://github.com/papa-marsh/maestro-scripts

## Why Maestro?

- **Type Safety**: Full type hints and IDE autocomplete for all entities and attributes
- **Python Power**: Use the full Python ecosystem—logic, libraries, conditionals, loops
- **Event-Driven**: Decorator-based triggers for state changes, schedules, and events
- **Fast Development**: Entity registry with autocomplete for all your Home Assistant devices
- **Easy Testing**: Write unit tests for your automations like any Python code

## Quick Start

### Prerequisites

- Python 3.13+
- Docker & Docker Compose
- Home Assistant instance with WebSocket API access

### Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/papa-marsh/maestro
   cd maestro
   ```

2. **Initialize version control for your scripts**

   ```bash
   cd scripts
   git init
   ```

   The `scripts/` directory is gitignored by the main repo, so you should create your own repository here to version control your automation logic.

3. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env with your Home Assistant URL, long-lived access token, etc.
   ```

   To create a new long-lived access token, navigate to the `<hass_url>/profile/security` page in Home Assistant.

   Pro tip: Create the access token using a separate account named "Maestro" to make it easy to see which actions were triggered by Maestro in an entity's state history.

4. **Start services or deploy new changes**

   ```bash
   make deploy
   ```

   **Note:** Whenever you make changes to your automation scripts, run `make deploy` to rebuild and restart the services with your latest changes.

5. **Verify WebSocket connection**

   Check the logs to confirm successful connection:

   ```bash
   make logs
   ```

   You should see:

   ```
   WebSocket authenticated successfully
   ```

## Writing Automations

All your automation logic goes in the `scripts/` directory. Import from the `maestro` package to access triggers, entities, and utilities.

### A Quick Note on Imports

Everything intended for use in automation scripts is exported from top-level `maestro` packages. You never need to import from deeper in the package structure.

```python
from maestro.domains import ON, OFF, HOME, AWAY        # State constants
from maestro.triggers import state_change_trigger       # Trigger decorators
from maestro.integrations import StateChangeEvent       # Event types
from maestro.registry import switch, light, sensor      # Entity instances
from maestro.utils import Notif, JobScheduler, log      # Utilities
from maestro.testing import MaestroTest                 # Test framework
```

### Basic Example

```python
# scripts/bedroom_lights.py
from maestro.domains import OFF, ON
from maestro.triggers import state_change_trigger
from maestro.integrations import StateChangeEvent
from maestro.registry import switch, light

@state_change_trigger(switch.bedroom_motion_sensor, to_state=ON)
def motion_detected(state_change: StateChangeEvent) -> None:
    """Turn on bedroom lights when motion detected"""
    light.bedroom_ceiling.turn_on()

@state_change_trigger(switch.bedroom_motion_sensor, to_state=OFF)
def motion_cleared(state_change: StateChangeEvent) -> None:
    """Turn off bedroom lights when motion clears"""
    light.bedroom_ceiling.turn_off()
```

### Schedule-Based Automation

```python
# scripts/morning_routine.py
from maestro.triggers import cron_trigger
from maestro.registry import switch, climate

@cron_trigger(hour=7, minute=0)
def morning_routine() -> None:
    """Run every morning at 7:00 AM"""
    switch.coffee_maker.turn_on()
    climate.bedroom_thermostat.set_temperature(72)
```

### Working with Entity State

```python
from maestro.triggers import state_change_trigger
from maestro.integrations import StateChangeEvent
from maestro.registry import sensor, switch

@state_change_trigger(sensor.outdoor_temperature)
def temperature_monitor(state_change: StateChangeEvent) -> None:
    """Control fan based on temperature"""
    # Note: entity state is always returned as a string
    temp = float(state_change.new.state)

    if temp > 75:
        switch.ceiling_fan.turn_on()
    elif temp < 68:
        switch.ceiling_fan.turn_off()
```

## Available Triggers

Trigger decorators automatically register your functions to respond to events. Decorated functions can optionally accept parameters that provide event context—these parameters are optional and the decorator works whether you include them or not.

**Note:** The script discovery logic ignores any module that starts with either `test` or an underscore `_` (including `__init__.py` modules)

**Note:** If a function belongs to a class, then it must be a `@staticmethod` in order to be decorated.

### State Change Trigger

Responds when an entity's state changes. Can trigger on one or multiple entities.

```python
# Single entity with filter
@state_change_trigger(switch.bedroom_motion_sensor, to_state=ON)
def motion_detected(state_change: StateChangeEvent) -> None:
    log.info("Motion detected", new_state=state_change.new.state)

# Multiple entities - same handler for all
@state_change_trigger(
    sensor.living_room_temperature,
    sensor.bedroom_temperature,
    sensor.kitchen_temperature
)
def temperature_changed(state_change: StateChangeEvent) -> None:
    log.info("Temperature changed", entity_id=state_change.entity_id)

# Without parameters - still works!
@state_change_trigger(switch.bedroom_motion_sensor)
def simple_handler() -> None:
    log.info("Entity changed")
```

**Decorator Parameters:**

- `*entities`: One or more Entity objects or entity ID strings
- `from_state`: Optional - only trigger when transitioning from this state
- `to_state`: Optional - only trigger when transitioning to this state

**Optional Function Parameters:**

- `state_change: StateChangeEvent` - Contains old and new state information

### Cron Trigger

Runs on a schedule using cron syntax.

```python
@cron_trigger(hour=7, minute=30)
def morning_task() -> None:
    pass

# Or use cron pattern
@cron_trigger(pattern="0 */6 * * *")  # Every 6 hours
def periodic_task() -> None:
    pass
```

**Decorator Parameters:**

- `pattern`: Cron pattern string (e.g., "0 0 \* \* \*")
- `minute`, `hour`, `day_of_month`, `month`, `day_of_week`: Individual cron fields

**Note:** You can use either `pattern` or individual fields, but not both.

**Optional Function Parameters:**

- None - cron triggers don't provide runtime parameters

### Sun Trigger

Runs based on solar events (sunrise, solar noon, dusk, etc.) with optional time offsets.

```python
from datetime import timedelta
from maestro.triggers import sun_trigger, SolarEvent

# At sunrise
@sun_trigger(SolarEvent.SUNRISE)
def sunrise_routine() -> None:
    switch.outdoor_lights.turn_off()

# 30 minutes before sunset
@sun_trigger(SolarEvent.DUSK, offset=timedelta(minutes=-30))
def pre_dusk() -> None:
    switch.patio_lights.turn_on()
```

**Decorator Parameters:**

- `solar_event`: SolarEvent enum value (`DAWN`, `DUSK`, `SOLAR_MIDNIGHT`, `SOLAR_NOON`, `SUNRISE`, `SUNSET`)
- `offset`: Optional timedelta (negative for before, positive for after). Max ±12 hours.

**Optional Function Parameters:**

- None - sun triggers don't provide runtime parameters

### Event Fired Trigger

Responds to custom Home Assistant events. Supports filtering by user ID and arbitrary event data key-value pairs.

```python
# Basic event trigger
@event_fired_trigger("my_custom_event")
def handle_event(event: FiredEvent) -> None:
    log.info("Event received", data=event.data)

# With event data filtering - only fires when event.data["trigger"] matches
@event_fired_trigger("my_custom_event", trigger="button_press")
def handle_button(event: FiredEvent) -> None:
    log.info("Button pressed")
```

**Decorator Parameters:**

- `event_type`: String matching the Home Assistant event type
- `user_id`: Optional - filter by user who triggered the event
- `**event_data`: Optional key-value filters applied to the event's data dict

**Optional Function Parameters:**

- `event: FiredEvent` - Contains event data and context

### Notification Action Trigger

Responds to notification actions (e.g., buttons pressed on push notifications).

```python
@notif_action_trigger("UNLOCK_DOOR")
def handle_unlock(notif_action: NotifActionEvent) -> None:
    door_id = notif_action.action_data.get("door_id")
    if door_id == "front_door":
        lock.front_door.unlock()
```

**Decorator Parameters:**

- `action`: String matching the notification action ID
- `device_id`: Optional - filter by specific device

**Optional Function Parameters:**

- `notif_action: NotifActionEvent` - Contains action data and device info

### Maestro Trigger

Runs on Maestro service lifecycle events.

```python
from maestro.triggers import maestro_trigger, MaestroEvent

@maestro_trigger(MaestroEvent.STARTUP)
def on_startup() -> None:
    """Runs when Maestro service starts"""
    log.info("Maestro started")

@maestro_trigger(MaestroEvent.SHUTDOWN)
def on_shutdown() -> None:
    """Runs when Maestro service shuts down"""
    log.info("Maestro shutting down")
```

### Home Assistant Trigger

Runs on Home Assistant lifecycle events (HA starting up or shutting down).

```python
from maestro.triggers import hass_trigger, HassEvent

@hass_trigger(HassEvent.STARTUP)
def on_ha_start() -> None:
    """Runs when Home Assistant starts"""
    log.info("Home Assistant started")
```

These are distinct from Maestro triggers—HA can restart independently while Maestro keeps running.

## Entity Registry

Maestro automatically populates a typed entity registry from your Home Assistant instance. Access entities with full autocomplete:

```python
from maestro.registry import switch, light, climate, sensor

# All your entities are available as typed objects
switch.living_room_lamp.turn_on()
climate.bedroom_thermostat.set_temperature(72)
temp = sensor.outdoor_temperature.state
```

The registry is code-generated from your HA instance's entities. Each entity has typed attributes accessible as properties:

```python
# State is always a string
state = sensor.outdoor_temperature.state

# Attributes are typed via EntityAttribute descriptors
battery = sensor.outdoor_temperature.battery_level   # int
friendly_name = sensor.outdoor_temperature.friendly_name  # str
```

## Entity Methods

Common methods available on entity objects:

### Light

```python
# rgb_color and temperature are required; brightness and transition have defaults
light.bedroom.turn_on(rgb_color=(255, 200, 150), temperature=3000)
light.bedroom.turn_on(rgb_color=(255, 200, 150), temperature=3000, brightness_percent=50)
light.bedroom.turn_off()
light.bedroom.turn_off(transition_seconds=5)
light.bedroom.toggle()
```

### Climate

```python
climate.thermostat.set_temperature(72)
climate.thermostat.set_hvac_mode("heat")
climate.thermostat.set_fan_mode("auto")
climate.thermostat.set_preset_mode("away")
climate.thermostat.turn_on()
climate.thermostat.turn_off()
```

### Switch

```python
switch.coffee_maker.turn_on()
switch.coffee_maker.turn_off()
switch.coffee_maker.toggle()
switch.coffee_maker.is_on  # bool property
```

### Lock

```python
lock.front_door.lock()
lock.front_door.unlock()
```

### Cover

```python
cover.garage_door.open_cover()
cover.garage_door.close_cover()
cover.garage_door.stop_cover()
cover.garage_door.toggle()
```

### Fan

```python
fan.ceiling_fan.turn_on()
fan.ceiling_fan.turn_off()
fan.ceiling_fan.set_speed(Fan.Speed.MEDIUM)  # LOW=33, MEDIUM=66, HIGH=100
```

### Media Player

```python
media_player.living_room.turn_on()
media_player.living_room.turn_off()
media_player.living_room.play(content_id="...", content_type="music")
media_player.living_room.pause()
media_player.living_room.set_volume(0.5)  # 0.0 to 1.0
media_player.living_room.next()
media_player.living_room.previous()
```

## Custom Domain Subclasses

You can extend built-in domain classes with device-specific or integration-specific functionality. Custom domains live in `scripts/custom_domains/` and are automatically injected into the `maestro.domains` namespace at startup.

**Important:** Import from the specific domain module (e.g., `maestro.domains.climate`), not the package (`maestro.domains`), to avoid circular imports.

### Example: Attribute Value Enums

Add type safety when passing argument values:

```python
# scripts/custom_domains/climate.py
from enum import StrEnum, auto
from typing import override

from maestro.domains.climate import Climate


class TeslaHVAC(Climate):
    class HVACMode(StrEnum):
        OFF = auto()
        HEAT_COOL = auto()

    class PresetMode(StrEnum):
        NORMAL = auto()
        DOG = auto()
        CAMP = auto()

    @override
    def set_hvac_mode(self, mode: HVACMode) -> None:  # type:ignore[override]
        self.perform_action("set_hvac_mode", hvac_mode=mode)

    @override
    def set_preset_mode(self, mode: PresetMode) -> None:  # type:ignore[override]
        self.perform_action("set_preset_mode", preset_mode=mode)
```

### Example: Extended Action Methods

When a HA integration exposes actions under a different domain:

```python
# scripts/custom_domains/sonos_speaker.py
from maestro.domains.media_player import MediaPlayer
from maestro.integrations import Domain


class SonosSpeaker(MediaPlayer):
    def join(self, members: list["SonosSpeaker"]) -> None:
        speaker_ids = [m.id for m in members]
        self.perform_action("join", group_members=speaker_ids)

    def unjoin(self) -> None:
        self.perform_action("unjoin")

    def snapshot(self, with_group: bool = False) -> None:
        # Sonos snapshot is under the "sonos" domain, not "media_player"
        self.state_manager.hass_client.perform_action(
            domain=Domain.SONOS, action="snapshot",
            entity_id=self.id, with_group=with_group,
        )
```

Custom domain classes must be exported from `scripts/custom_domains/__init__.py`:

```python
# scripts/custom_domains/__init__.py
from .climate import TeslaHVAC
from .sonos_speaker import SonosSpeaker

__all__ = [
    TeslaHVAC.__name__,
    SonosSpeaker.__name__,
]
```

Once defined, registry-generated entity classes automatically inherit from your custom subclass instead of the base domain class.

## Sending Push Notifications

Maestro includes a push notification system for iOS devices via Home Assistant. Supports priorities, actionable buttons, custom sounds, and grouping.

### Basic Notification

```python
from maestro.utils import Notif
from maestro.registry import person

# Create and send a notification
Notif(
    message="Motion detected in living room",
    title="Security Alert",
    priority=Notif.Priority.TIME_SENSITIVE,
).send(person.john_doe)

# Send to multiple people (variadic, not a list)
Notif(
    message="Good morning!",
    title="Daily Briefing",
).send(person.john_doe, person.jane_doe)
```

### Notification Priorities

```python
# PASSIVE      - Silent, no wake screen
# ACTIVE       - Standard notification (default)
# TIME_SENSITIVE - Bypasses notification summary
# CRITICAL     - Plays sound even on silent mode

Notif(
    message="Critical alert",
    priority=Notif.Priority.CRITICAL,
).send(person.john_doe)
```

### Actionable Notifications

```python
# Build action buttons
unlock_action = Notif.build_action(
    name="UNLOCK_DOOR",
    title="Unlock Door",
    destructive=False,
    require_auth=True,
)
ignore_action = Notif.build_action(
    name="IGNORE",
    title="Ignore",
    destructive=True,
)

# Send notification with actions
Notif(
    message="Someone is at the door",
    title="Doorbell",
    actions=[unlock_action, ignore_action],
    action_data={"door_id": "front_door"},  # Passed back to trigger handler
).send(person.john_doe)
```

### Handling Notification Actions

```python
from maestro.triggers import notif_action_trigger
from maestro.integrations import NotifActionEvent
from maestro.registry import lock

@notif_action_trigger("UNLOCK_DOOR")
def handle_unlock(notif_action: NotifActionEvent) -> None:
    door_id = notif_action.action_data.get("door_id")
    if door_id == "front_door":
        lock.front_door.unlock()
```

### Advanced Options

```python
Notif(
    message="Message content",
    title="Title",
    priority=Notif.Priority.ACTIVE,
    group="alarm_system",               # Group related notifications
    tag="front_door",                   # Replace previous notification with same tag
    sound="alarm.caf",                  # Custom sound file (None for silent)
    url="/lovelace-mobile/cameras",     # Open specific view when tapped
)
```

## Scheduling Jobs

Schedule one-off functions to run at a specific time. Jobs persist across restarts via Redis.

```python
from datetime import timedelta
from maestro.utils import JobScheduler, local_now
from maestro.registry import light

def delayed_light_off() -> None:
    """Turn off lights after delay"""
    light.bedroom_ceiling.turn_off()

# Schedule job to run 30 minutes from now
scheduler = JobScheduler()
run_time = local_now() + timedelta(minutes=30)
job_id = scheduler.schedule_job(run_time=run_time, func=delayed_light_off)

# Cancel if needed
scheduler.cancel_job(job_id)
```

Jobs can accept keyword arguments:

```python
def set_temperature(temp: int) -> None:
    climate.thermostat.set_temperature(temp)

scheduler = JobScheduler()
scheduler.schedule_job(
    run_time=local_now() + timedelta(hours=1),
    func=set_temperature,
    func_params={"temp": 72},
)
```

## Testing Your Automations

Maestro includes a testing framework that lets you unit test your automations without a running Home Assistant instance. Tests use in-memory mocks and require no Redis or HA connection.

**Key Features:**

- **Automatic mocking** - All entities automatically use test mocks, no manual setup required
- **In-memory state** - State and actions are tracked in memory, no external dependencies
- **Trigger simulation** - Test state changes, events, and notification actions
- **Action assertions** - Verify that your automations call the correct Home Assistant actions

### Quick Example

```python
# scripts/tests/test_bedroom_lights.py
from maestro.domains import OFF, ON
from maestro.integrations import Domain
from maestro.registry import light, switch
from maestro.testing import MaestroTest

# Import the module you want to test to register its triggers
from scripts import bedroom_lights

def test_motion_turns_on_light(mt: MaestroTest) -> None:
    """Test that motion triggers the bedroom light"""
    mt.set_state(switch.bedroom_motion_sensor, OFF)
    mt.set_state(light.bedroom_ceiling, OFF)

    mt.trigger_state_change(switch.bedroom_motion_sensor, old=OFF, new=ON)

    mt.assert_action_called(Domain.LIGHT, "turn_on", entity_id=light.bedroom_ceiling.id)
```

**Note:** You must import the script module(s) you want to test. This registers the trigger decorators so they can be invoked by `trigger_state_change()` and similar methods.

### Common Testing Patterns

**Test state changes:**

```python
def test_temperature_control(mt: MaestroTest) -> None:
    mt.set_state(sensor.temperature, "70")
    mt.trigger_state_change(sensor.temperature, old="70", new="76")
    mt.assert_action_called(Domain.SWITCH, "turn_on", entity_id=switch.fan.id)
```

**Test custom events:**

```python
def test_custom_event(mt: MaestroTest) -> None:
    mt.trigger_event("my_custom_event", data={"duration": 30})
    mt.assert_action_called(Domain.NOTIFY, person.john.notify_action_name)
```

**Test multiple scenarios in one test:**

```python
def test_motion_sequence(mt: MaestroTest) -> None:
    mt.set_state(light.bedroom, OFF)

    mt.trigger_state_change(switch.motion, old=OFF, new=ON)
    mt.assert_action_called(Domain.LIGHT, "turn_on")

    mt.clear_action_calls()

    mt.trigger_state_change(switch.motion, old=ON, new=OFF)
    mt.assert_action_called(Domain.LIGHT, "turn_off")
```

### Running Tests

```bash
# Run all script tests
pytest scripts

# Run a specific test file
pytest scripts/tests/test_bedroom_lights.py

# Run a single test function
pytest scripts/tests/test_bedroom_lights.py::test_motion_turns_on_light
```

## Development Workflow

### Interactive Shell

```bash
# Flask shell with pre-loaded imports (StateManager, RedisClient, etc.)
make shell

# Direct bash access to the container
make bash
```

### Working with the Database

Maestro includes PostgreSQL and Flask-SQLAlchemy for persistent storage.

**Define models:**

```python
# scripts/my_automation/models.py
from typing import ClassVar

from maestro.app import db


class MyModel(db.Model):  # type:ignore[name-defined]
    __tablename__ = "my_table"
    __table_args__: ClassVar = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
```

**Create tables:**

```bash
make shell
>>> from maestro.app import db
>>> db.create_all()  # Creates all tables from imported models
```

**Query data:**

```python
from maestro.app import db
from scripts.my_automation.models import MyModel

# Query
items = db.session.query(MyModel).all()
item = db.session.query(MyModel).filter_by(name="example").first()

# Insert
new_item = MyModel(name="test")
db.session.add(new_item)
db.session.commit()

# Delete
db.session.delete(item)
db.session.commit()
```

**Note:** This project doesn't use migrations. Schema changes require manual SQL or `db.drop_all()` + `db.create_all()` (loses data).

## Example: Complete Automation

```python
# scripts/bedtime_routine/models.py
from typing import ClassVar

from maestro.app import db


class SnoozeHistory(db.Model):  # type:ignore[name-defined]
    __tablename__ = "snooze_history"
    __table_args__: ClassVar = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
```

```python
# scripts/bedtime_routine/__init__.py
from maestro.app import db
from maestro.domains import HOME
from maestro.integrations import StateChangeEvent, NotifActionEvent
from maestro.registry import switch, light, climate, person
from maestro.triggers import state_change_trigger, cron_trigger, notif_action_trigger
from maestro.utils import Notif, JobScheduler, local_now

from .models import SnoozeHistory

SNOOZE_MINUTES = 15
SNOOZE_JOB_ID = "bedtime_snooze"


@cron_trigger(hour=22, minute=0)
def bedtime_warning() -> None:
    """Notify 30 min before lights out"""
    snooze_action = Notif.build_action(name="SNOOZE_BEDTIME", title="Snooze 15 min")
    dismiss_action = Notif.build_action(name="DISMISS_BEDTIME", title="Dismiss")

    Notif(
        title="Bedtime Soon",
        message="Lights will turn off in 30 minutes",
        actions=[snooze_action, dismiss_action],
    ).send(person.john)


@cron_trigger(hour=22, minute=30)
def bedtime_routine() -> None:
    """Execute bedtime routine"""
    light.bedroom.turn_on(brightness_percent=20)
    light.living_room.turn_off()
    climate.bedroom.set_temperature(68)
    switch.sound_machine.turn_on()


@notif_action_trigger("SNOOZE_BEDTIME")
def snooze_bedtime_routine(notif_action: NotifActionEvent) -> None:
    """Delay bedtime routine and track snooze history"""
    snooze = SnoozeHistory(timestamp=local_now(), duration_minutes=SNOOZE_MINUTES)
    db.session.add(snooze)
    db.session.commit()

    Notif(
        title="Bedtime Snoozed",
        message=f"Routine delayed by {SNOOZE_MINUTES} minutes",
    ).send(person.john)


@state_change_trigger(person.john, to_state=HOME)
def welcome_home(state_change: StateChangeEvent) -> None:
    """Turn on lights if arriving home late"""
    hour = local_now().hour
    if 22 <= hour <= 23:
        light.living_room.turn_on()
```

## Troubleshooting

### WebSocket Connection Issues

**Problem**: Maestro can't connect to Home Assistant WebSocket

**Solutions**:

1. Verify `HOME_ASSISTANT_URL` in `.env` is correct (e.g., `http://192.168.1.100:8123`)
2. Verify `HOME_ASSISTANT_TOKEN` is a valid long-lived access token
3. Check Home Assistant is accessible: `curl http://<your-ha-url>/api/`
4. Review Maestro logs: `make logs`

**Problem**: WebSocket keeps reconnecting

**Solutions**:

1. Check network stability between Maestro and Home Assistant
2. Verify Home Assistant isn't restarting frequently
3. Check Home Assistant logs for WebSocket errors

**Problem**: Events seem to be missing

After reconnection, Maestro automatically syncs all entity states if it was disconnected for more than 30 minutes. If you still see issues:

1. Check logs for "State sync completed" message after reconnection
2. Verify the entity's domain is not in `DOMAIN_IGNORE_LIST`
3. Enable debug logging to see all events: Set `LOG_LEVEL=DEBUG` in `.env`

## Contributing

Maestro is actively developed but doesn't yet cover all Home Assistant domains, actions, and features. If you find something missing:

- **Entity domains**: Add new domain classes in `maestro/domains/`
- **Entity methods**: Extend existing domain classes with additional actions
- **Trigger types**: Implement new trigger decorators in `maestro/triggers/`
- **Utilities**: Add helpful utilities in `maestro/utils/`

Pull requests are welcome!

## License

MIT License - see [LICENSE](LICENSE)

## Support

For issues and questions, see the [GitHub Issues](https://github.com/papa-marsh/maestro/issues).
