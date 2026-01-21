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
   docker logs maestro | grep WebSocket
   ```

   You should see:

   ```
   WebSocket authenticated successfully
   ```

## Writing Automations

All your automation logic goes in the `scripts/` directory. Import from the `maestro` package to access triggers, entities, and utilities.

### A Quick Note On Imports

Anything intended to be used in automation logic is exported by a top-level package in the `maestro` directory. Importing from deeper in the package structure is never necessary.

**Examples**

- `from maestro.triggers import state_change_trigger`
- `from maestro.integrations import EntityId`

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
# Single entity
@state_change_trigger(switch.bedroom_motion_sensor, to_state=ON)
def motion_detected(state_change: StateChangeEvent) -> None:
    log.info(f"Changed from {state_change.old.state} to {state_change.new.state}")

# Multiple entities - same handler for all
@state_change_trigger(
    sensor.living_room_temperature,
    sensor.bedroom_temperature,
    sensor.kitchen_temperature
)
def temperature_changed(state_change: StateChangeEvent) -> None:
    log.info(f"{state_change.entity_id} changed to {state_change.new.state}")

# Without parameters - still works!
@state_change_trigger(entity)
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

**Optional Function Parameters:**

- None - cron triggers don't provide runtime parameters

### Event Fired Trigger

Responds to custom Home Assistant events.

```python
# With optional event parameter
@event_fired_trigger("my_custom_event")
def handle_event(event: FiredEvent) -> None:
    print(f"Event data: {event.data}")

# Without parameters
@event_fired_trigger("my_custom_event")
def simple_handler() -> None:
    print("Event fired")
```

**Decorator Parameters:**

- `event_type`: String matching the Home Assistant event type
- `user_id`: Optional - filter by user who triggered the event

**Optional Function Parameters:**

- `event: FiredEvent` - Contains event data and context

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
@sun_trigger(SolarEvent.SOLAR_NOON, offset=timedelta(minutes=-30))
def pre_sunset() -> None:
    switch.sprinklers.turn_on()
```

**Decorator Parameters:**

- `solar_event`: SolarEvent enum value
- `offset`: Optional - timedelta offset (negative for before, positive for after)

**Optional Function Parameters:**

- None - sun triggers don't provide runtime parameters

### Notification Action Trigger

Responds to notification actions (e.g., buttons pressed on push notifications).

```python
# With optional notif_action parameter
@notif_action_trigger("ACTION_ID")
def handle_action(notif_action: NotifActionEvent) -> None:
    print(f"Action data: {notif_action.action_data}")

# Without parameters
@notif_action_trigger("ACTION_ID")
def simple_handler() -> None:
    print("Action pressed")
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
    log.info("Maestro started!")

@maestro_trigger(MaestroEvent.SHUTDOWN)
def on_shutdown() -> None:
    """Runs when Maestro service shuts down"""
    log.info("Maestro shutting down")
```

**Decorator Parameters:**

- `event`: `MaestroEvent.STARTUP` or `MaestroEvent.SHUTDOWN`

**Optional Function Parameters:**

- None - maestro triggers don't provide runtime parameters

## Entity Registry

Maestro automatically populates a typed entity registry from your Home Assistant instance. Access entities with full autocomplete:

```python
from maestro.registry import switch, light, climate, sensor

# All your entities are available as typed objects
switch.living_room_lamp.turn_on()
climate.bedroom_thermostat.set_temperature(72)
temp = sensor.outdoor_temperature.state
```

## Entity Methods

Common methods available on entity objects:

### Light

```python
light.bedroom.turn_on(brightness=255, color_temp=300)
light.bedroom.turn_off()
light.bedroom.toggle()
```

### Climate

```python
climate.thermostat.set_temperature(72)
climate.thermostat.set_hvac_mode("heat")
climate.thermostat.turn_on()
climate.thermostat.turn_off()
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
```

## Accessing State & Attributes

```python
from maestro.registry import sensor

# Get current state
temp = sensor.outdoor_temperature.state

# Access attributes as EntityAttribute properties
battery = sensor.outdoor_temperature.battery_level
```

## Sending Push Notifications

Maestro includes a comprehensive push notification system with support for priorities, actionable notifications, and more.

### Basic Notification

```python
from maestro.utils import Notif, NotifPriority
from maestro.registry import person

# Create and send a notification
notif = Notif(
    message="Motion detected in living room",
    title="Security Alert",
    priority=NotifPriority.TIME_SENSITIVE
)
notif.send(person.john_doe)

# Send to multiple people
notif.send([person.john_doe, person.jane_doe])
```

### Notification Priorities

```python
from maestro.utils import NotifPriority

# PASSIVE - Silent, no wake screen
# ACTIVE - Standard notification (default)
# TIME_SENSITIVE - Bypasses notification summary
# CRITICAL - Plays sound even on silent mode

notif = Notif(
    message="Critical alert",
    priority=NotifPriority.CRITICAL
)
```

### Actionable Notifications

```python
from maestro.utils import Notif

# Build actions with the helper method
action1 = Notif.build_action(
    name="UNLOCK_DOOR",
    title="Unlock Door",
    destructive=False,
    require_auth=True
)
action2 = Notif.build_action(
    name="IGNORE",
    title="Ignore",
    destructive=True
)

# Create notification with actions
notif = Notif(
    message="Someone is at the door",
    title="Doorbell",
    actions=[action1, action2],
    action_data={"door_id": "front_door"}  # Passed to trigger handler
)
notif.send(person.john_doe)
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
notif = Notif(
    message="Message content",
    title="Title",
    priority=NotifPriority.ACTIVE,
    group="alarm_system",  # Group related notifications
    tag="front_door",      # Replace previous notification with same tag
    sound="alarm.caf",     # Custom sound file
    url="/lovelace-mobile/cameras"  # Open specific view when tapped
)
```

## Scheduling Jobs

Schedule one-off functions to run at a specific time. Jobs persist across restarts via Redis.

```python
from datetime import timedelta
from maestro.utils import JobScheduler, local_now
from maestro.registry import light

def delayed_light_off():
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
def set_temperature(temp: int):
    climate.thermostat.set_temperature(temp)

scheduler.schedule_job(
    run_time=local_now() + timedelta(hours=1),
    func=set_temperature,
    func_params={"temp": 72}
)
```

## Testing Your Automations

Maestro includes a comprehensive testing framework that lets you unit test your automations without affecting your production Home Assistant instance. Tests use in-memory mocks and require no Redis or Home Assistant connection.

**Key Features:**

- **Automatic mocking** - All entities automatically use test mocks, no manual setup required
- **In-memory state** - State and actions are tracked in memory, no external dependencies
- **Trigger simulation** - Test state changes, events, and cron triggers
- **Action assertions** - Verify that your automations call the correct Home Assistant actions

### Quick Example

```python
# scripts/test_bedroom_lights.py
from maestro.registry import light, switch
from maestro.testing import MaestroTest

# Import the module you want to test to register its triggers
from scripts.bedroom import lights

def test_motion_turns_on_light(mt: MaestroTest):
    # Setup: Set initial entity states
    mt.set_state(switch.motion_sensor, OFF)
    mt.set_state(light.bedroom, OFF)

    # Act: Trigger your automation by simulating a state change
    mt.trigger_state_change(switch.motion_sensor, old=OFF, new=ON)

    # Assert: Verify the light was turned on
    mt.assert_action_called("light", "turn_on", entity_id="light.bedroom")
```

**Note:** You must import the script module(s) you want to test. This registers the trigger decorators (`@state_change_trigger`, etc.) so they can be invoked by `trigger_state_change()` and similar methods.

### Common Testing Patterns

**Test state changes:**

```python
def test_temperature_control(mt: MaestroTest):
    mt.set_state(sensor.temperature, "70")
    mt.trigger_state_change(sensor.temperature, old="70", new="76")
    mt.assert_action_called("switch", "turn_on", entity_id="switch.fan")
```

**Test custom events:**

```python
def test_custom_event(mt: MaestroTest):
    mt.trigger_event("something_happened", data={"duration": 30})
    mt.assert_action_called("notify", "mobile_app", message="Something happened!")
```

**Test with entity objects (automatically mocked):**

```python
def test_with_entities(mt: MaestroTest):
    mt.set_state(light.bedroom, OFF)

    # Entities automatically use the test's mock state manager - no setup needed!
    light.bedroom.turn_on(rgb_color=(255, 255, 255), temperature=4000)
    mt.assert_action_called("light", "turn_on")
```

**Test multiple scenarios:**

```python
def test_motion_sequence(mt: MaestroTest):
    mt.set_state("light.bedroom", OFF)

    mt.trigger_state_change("switch.motion", OFF, ON)
    mt.assert_action_called("light", "turn_on")

    mt.clear_action_calls()

    mt.trigger_state_change("switch.motion", ON, OFF)
    mt.assert_action_called("light", "turn_off")
```

### Running Tests

```bash
# Run tests (with venv activated)
pytest scripts
```

## Development Workflow

### Interactive Shell

```bash
# Flask shell with pre-loaded imports
make shell

# Direct bash access
make bash
```

### Working with the Database

Maestro includes PostgreSQL and Flask-SQLAlchemy for persistent storage.

**Define models:**

```python
# scripts/my_automation/models.py
from maestro.app import db

class MyModel(db.Model):
    __tablename__ = "my_table"
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
from maestro.app import db

class SnoozeHistory(db.Model):  # type:ignore [name-defined]
    __tablename__ = "snooze_history"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
```

```python
# scripts/bedtime_routine/__init__.py
from maestro.app import db
from maestro.triggers import state_change_trigger, cron_trigger, notif_action_trigger
from maestro.integrations import StateChangeEvent, NotifActionEvent
from maestro.registry import switch, light, climate, person
from maestro.utils import Notif, local_now

from .models import SnoozeHistory

@cron_trigger(hour=22, minute=0)  # 10 PM daily
def bedtime_warning() -> None:
    """Notify 30 min before lights out"""
    snooze_action = Notif.build_action(
        name="SNOOZE_BEDTIME",
        title="Snooze 15 min"
    )
    dismiss_action = Notif.build_action(
        name="DISMISS_BEDTIME",
        title="Dismiss"
    )

    notif = Notif(
        title="Bedtime Soon",
        message="Lights will turn off in 30 minutes",
        actions=[snooze_action, dismiss_action]
    )
    notif.send(person.john)

@cron_trigger(hour=22, minute=30)  # 10:30 PM daily
def bedtime_routine() -> None:
    """Execute bedtime routine"""
    light.bedroom.turn_on(brightness=50)  # Dim lights
    light.living_room.turn_off()
    climate.bedroom.set_temperature(68)
    switch.sound_machine.turn_on()

@notif_action_trigger("SNOOZE_BEDTIME")
def snooze_bedtime_routine(notif_action: NotifActionEvent) -> None:
    """Delay bedtime routine by 15 minutes and track snooze"""
    # Log snooze to database
    snooze = SnoozeHistory(timestamp=local_now(), duration_minutes=15)
    db.session.add(snooze)
    db.session.commit()

    # Reschedule bedtime routine (implementation would schedule a one-time job)
    notif = Notif(
        title="Bedtime Snoozed",
        message="Routine delayed by 15 minutes"
    )
    notif.send(person.john)

@state_change_trigger(person.john, to_state=HOME)
def welcome_home(state_change: StateChangeEvent) -> None:
    """Cancel bedtime routine if arriving home late"""
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
4. Review Maestro logs: `docker logs maestro`

**Problem**: WebSocket keeps reconnecting

**Solutions**:

1. Check network stability between Maestro and Home Assistant
2. Verify Home Assistant isn't restarting frequently
3. Check Home Assistant logs for WebSocket errors

**Problem**: Events seem to be missing

After reconnection, Maestro automatically syncs all entity states. If you still see issues:

1. Check logs for "State sync completed" message after reconnection
2. Verify the entity is not in `DOMAIN_IGNORE_LIST`
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
