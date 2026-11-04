# Maestro

Personal Home Assistant automations built on the [Maestro framework](https://github.com/papa-marsh/hass-maestro) (`hass-maestro` on PyPI, imported as `maestro`). This is a standalone application: `app.py` constructs the `MaestroApp`, and the project runs in Docker alongside Redis and Postgres.

Maestro's architecture, code style, type system, and testing infrastructure are documented in the library's AGENTS.md (`../hass-maestro/AGENTS.md` when developing locally). Everything there (code style, naming conventions, type annotations, error handling, logging) applies here too.

This repo is also the reference consumer that hass-maestro's `init` scaffolding mirrors: files like the Dockerfile, docker-compose.yml, justfile, redis.conf, pyproject.toml, and AGENTS.md have template counterparts in `../hass-maestro/maestro/_cli/templates/`. When changing one of these files, check whether its template should be updated to match.

## Project Structure

```
app.py                # Entrypoint: constructs MaestroApp from env vars; gunicorn serves "app:app"
scripts/              # Automation modules, auto-imported at startup as the `scripts` package
  common/             # Shared utilities used across domains (gates, event types, finance API, DB types)
  config/             # Secrets and zone metadata (gitignored -- contains personal data)
  <domain>/           # Thematic automation dirs (home/, vehicles/, family/, frontend/, ...)
custom_domains/       # Entity subclass extensions; imported by maestro at startup
registry/             # Generated entity registry (committed); imported as `from registry import ...`
Dockerfile / docker-compose.yml / justfile   # Deployment (maestro + redis + postgres)
```

The three project packages (`scripts`, `registry`, `custom_domains`) are top-level packages rooted at the repo root, which `MaestroApp` puts on `sys.path`. Script modules import as `scripts.home.thermostat`.

## Build / Lint / Test Commands

All commands run from the repo root.

```bash
uv sync                    # Install dependencies (hass-maestro resolves from PyPI)

uv run pytest              # Run all tests
uv run pytest scripts/home/tests/test_thermostat.py::test_check_thermostat_hold
uv run pytest -k "test_charging"

uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run mypy .              # Type check (strict)

# Deployment (on maestro server)
just deploy                # Rebuild and restart all services
just pull-deploy           # Pull main, then deploy
just upgrade-maestro       # Re-lock the hass-maestro dependency, then deploy
just logs                  # Tail maestro container logs
just shell                 # Flask shell (background services disabled) with pre-loaded imports
just prune                 # Remove registry entities no longer in Home Assistant
```

The `mt` test fixture auto-registers via hass-maestro's pytest plugin -- no conftest wiring. Tests need no Redis, HA, or Postgres.

## Imports

### From Maestro (always via top-level package re-exports)

```python
from maestro import db, get_config
from maestro.domains import ON, OFF, HOME, AWAY, UNAVAILABLE, UNKNOWN
from maestro.exceptions import AttributeDoesNotExistError
from maestro.integrations import StateChangeEvent, FiredEvent, Domain, EntityId
from maestro.registry import RegistryManager
from maestro.triggers import state_change_trigger, cron_trigger, event_fired_trigger
from maestro.utils import Notif, JobScheduler, local_now, format_duration, log
from maestro.testing import MaestroTest
```

Never import from submodules -- everything consumable is re-exported from a top-level package (internal modules carry an `_` prefix). This includes `from maestro import get_config`, `from maestro.registry import RegistryManager`, and `from maestro.exceptions import <XxxError>`.

### From project packages

```python
from registry import person, switch, sensor, climate, binary_sensor, cover
from custom_domains import Thermostat, SonosSpeaker
from scripts.common.gates import GateManager, gate_check, Gate
from scripts.config.secrets import USER_ID_TO_PERSON, PERSON_TO_USER_ID
```

Within a domain, use relative imports for sibling modules:

```python
from .common import Nyx, Tess, get_vehicle_config
from .door_left_open import EXTERIOR_DOORS
```

## Custom Domains (`custom_domains/`)

Custom domain subclasses extend maestro's base domain classes with device-specific functionality. Maestro imports this package at startup (configured via `custom_domains_dir`), before registry modules and scripts load. Registry-generated entity classes can inherit from these instead of base domain classes; the registry generator preserves custom parents and imports them from this package.

The pattern:
```python
from maestro.domains import Climate

class Thermostat(Climate):
    class HVACMode(StrEnum):
        OFF = auto()
        COOL = auto()
        HEAT = auto()

    @override
    def set_hvac_mode(self, mode: HVACMode) -> None:  # type:ignore[override]
        self.perform_action("set_hvac_mode", hvac_mode=mode)
```

- Nested `StrEnum` classes define typed mode/preset constants
- `@override` + `# type:ignore[override]` on methods that narrow parameter types
- Export via `__all__` in `custom_domains/__init__.py` using `ClassName.__name__`

Current custom domains: `Thermostat`, `BathroomFloor`, `TeslaHVAC`, `SonosSpeaker`, `SprinklerZone`, `ZoneExtended`, `GoogleCalendar`, `Marshall`, `Emily`

## Registry (`registry/`)

Generated by maestro's `RegistryManager` (with `autopopulate_registry=True` in production, entries refresh automatically as state changes arrive). The generated modules are **gitignored** -- they enumerate the home's entities, which stays out of the public repo -- but must exist on disk for scripts, tests, and Docker builds. Don't hand-edit entity entries except to change a class's parent to a custom domain subclass -- the generator preserves that. `just prune` removes entities that no longer exist in HA.

## Automation Patterns

### Trigger Decorators

```python
# State change -- single entity with filter
@state_change_trigger(switch.space_heater, to_state=ON)
def handler(state_change: StateChangeEvent) -> None: ...

# State change -- spread a list of entities
@state_change_trigger(*EXTERIOR_DOORS)
def handler() -> None: ...

# Cron -- daily at specific hour
@cron_trigger(hour=19)
def nightly_check() -> None: ...

# Cron -- stacked for multiple schedules
@cron_trigger(hour=8)
@cron_trigger(hour=20)
def check_twice_daily() -> None: ...

# Custom event
@event_fired_trigger(EventType.BATHROOM_FLOOR)
def handler(event: FiredEvent) -> None: ...

# HA lifecycle (runs on HA restart and maestro restart)
@hass_trigger(HassEvent.STARTUP)
@maestro_trigger(MaestroEvent.STARTUP)
def initialize() -> None: ...
```

Functions can accept event parameters or take no parameters -- the framework uses `inspect.signature()` to match.

### Guard Clauses

Always guard against `UNAVAILABLE`/`UNKNOWN` states and irrelevant conditions early:

```python
if state_change.old.state == UNAVAILABLE:
    return
if not person.emily.is_home:
    return
```

### Entity State Access

Entity state is always a string. Cast for numeric comparisons:

```python
temp = float(climate.thermostat.current_temperature)
battery = int(sensor.nyx_battery.state)
```

Use convenience properties where available: `.is_on`, `.is_home`, `.friendly_name`.

### Push Notifications

```python
Notif(
    title="Alert Title",
    message="Alert message",
    priority=Notif.Priority.TIME_SENSITIVE,
    tag="unique_tag",
).send(person.marshall, person.emily)
```

### Firing HA Events

```python
person.marshall.state_manager.hass_client.fire_event(EventType.BATHROOM_FLOOR, key="value")
```

Fires onto the HA event bus and round-trips through the websocket, so matching
`event_fired_trigger` functions (and any HA automations) will fire.

Include a `user_id` key in the event data to fire on behalf of a specific user: it takes
precedence over the event's context user (which for REST-fired events is just maestro's
token owner) when the framework builds `FiredEvent.user_id`.

### Job Scheduler (Debounce / Delayed Execution)

```python
JOB_ID = "descriptive_job_id"

# Schedule
JobScheduler().schedule_job(
    run_time=local_now() + timedelta(minutes=30),
    func=callback_function,
    func_params={"key": value},
    job_id=JOB_ID,
)

# Cancel
JobScheduler().cancel_job(JOB_ID)
```

Job IDs are module-level `SCREAMING_SNAKE_CASE` constants. `JobScheduler()` is instantiated per-use (auto-detects test mode).

### Database Models

```python
from maestro import db

class ZoneChange(db.Model):  # type:ignore[name-defined]
    __tablename__ = "zone_change"
    __table_args__: ClassVar = {"extend_existing": True}

    person = db.Column(db.String, primary_key=True, nullable=False)
    arrived_at = db.Column(TZDateTime, primary_key=True, nullable=False)
```

- `# type:ignore[name-defined]` on `db.Model` (dynamic base class)
- `__tablename__` is explicit, `snake_case`, singular
- `__table_args__: ClassVar = {"extend_existing": True}` required
- Use `TZDateTime` from `scripts.common.db_types` for timezone-aware datetime columns
- `__repr__` for debug output

### Redis Queries

```python
redis = entity.state_manager.redis_client
key = redis.build_key(PREFIX, identifier)
redis.set(key=key, value=value.isoformat(), ttl_seconds=IntervalSeconds.TWO_WEEKS)
result = redis.get(key=key)
```

Key prefixes are module-level constants (maestro namespaces all keys under its configured `redis_key_prefix` automatically). TTLs use `IntervalSeconds` enum values. Timestamps serialize as ISO strings.

## Testing

### Structure

- Test files mirror automation modules: `test_thermostat.py` tests `thermostat.py`
- All test functions are module-level (no test classes)
- Every test takes `mt: MaestroTest` as its first parameter (required for any test touching state, triggers, or the DB)
- Return type always `-> None`
- Import the script module via relative import to register its triggers:
  ```python
  from .. import thermostat
  ```

### Pattern: Setup / Trigger / Assert

```python
def test_high_charge_limit(mt: MaestroTest) -> None:
    # Setup
    mt.set_state(binary_sensor.nyx_charger, OFF)
    mt.set_state(number.nyx_charge_limit, str(DEFAULT_CHARGE_LIMIT))

    # Trigger
    mt.trigger_state_change(binary_sensor.nyx_charger, new=ON)

    # Assert
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)
```

### Multi-Scenario Tests

Use `mt.clear_action_calls()` between scenarios within a single test:

```python
def test_meeting_notifications(mt: MaestroTest) -> None:
    # Scenario 1: Emily away -- no notification
    mt.set_state(person.emily, AWAY)
    mt.trigger_state_change(maestro.meeting_active, new=ON)
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)

    # Scenario 2: Emily arrives -- notification sent
    mt.trigger_state_change(person.emily, new=HOME)
    mt.assert_action_called(Domain.NOTIFY, person.emily.notify_action_name)
    mt.clear_action_calls()
```

### Key Assertions

```python
mt.assert_action_called(Domain.LIGHT, "turn_on", entity_id=light.bedroom.id)
mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)
mt.assert_job_scheduled(JOB_ID, target_function)
mt.assert_job_not_scheduled(JOB_ID)
mt.assert_state(maestro.meeting_active, ON)
mt.assert_entity_exists(maestro.meeting_active)
mt.assert_event_fired(EventType.BATHROOM_FLOOR)
mt.assert_event_not_fired(EventType.ADMIN_EVENT)
```

Notifications are asserted as action calls on `Domain.NOTIFY` with the person's `notify_action_name`. Entity arguments to assertions are passed as `.id` strings, not Entity objects.

### Calling Non-Triggered Functions

Test helper/utility functions by calling them directly:

```python
bathroom_floor.reset_floor_to_auto()
mt.assert_action_called(Domain.CLIMATE, "set_preset_mode")
```

Cron- and sun-triggered functions can also be called directly -- in test mode the trigger wrapper executes the function without requiring a running app.

### Time Mocking

```python
with mt.mock_datetime_as(local_now().replace(hour=3, minute=0)):
    mt.trigger_state_change(...)
    mt.assert_action_called(...)
```

## Config (`scripts/config/`)

- `secrets.py` -- User ID mappings (`USER_ID_TO_PERSON`, `PERSON_TO_USER_ID`), API tokens, financial constants. **Gitignored.**
- `zones.py` -- `ZoneMetadata` dataclass and `zone_metadata_registry` dict mapping zone names to rich metadata (short names, debounce durations, region flags, geographic groupings). **Gitignored.**

Both are gitignored because they contain personal data. If you need to modify them, note that changes won't appear in git status.

## Deployment

Runs on the user's mac mini via Docker Compose (maestro + redis + postgres). Runtime configuration comes from `.env` (see `.env.example`); `app.py` owns all env parsing. The `hass-maestro` dependency resolves from PyPI (constrained in `pyproject.toml`, pinned in `uv.lock`); run `just upgrade-maestro` to pick up the latest library release. The generated `registry/` modules are gitignored (they describe the home's entity inventory) -- when setting up a fresh checkout, copy them from an existing deployment or let maestro regenerate them against live HA. `MAESTRO_BACKGROUND_SERVICES=false` disables the websocket and scheduler (used by `just shell` and `just prune`).
