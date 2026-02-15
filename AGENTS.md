# Maestro

Strongly-typed Python automation framework for Home Assistant. Flask + SQLAlchemy + Redis + APScheduler + structlog. Runs in Docker, connects to Home Assistant via WebSocket and REST API. Python 3.13+.

## Project Structure

```
maestro/                  # Main package (the framework)
  app.py                  # Flask app factory, db/app singletons, startup orchestration
  config.py               # All env-var configuration (flat module, read at import time)
  domains/                # Entity domain classes (Light, Switch, Climate, etc.)
  handlers/               # WebSocket event handler functions (state_changed, event_fired, etc.)
  integrations/           # External service clients (HA REST, WebSocket, Redis, StateManager)
  triggers/               # Decorator-based trigger system (state_change, cron, sun, etc.)
  registry/               # Auto-generated entity registry (code-generated, relaxed linting)
  testing/                # Test framework (MaestroTest, mocks, fixtures)
    tests/                # Self-tests for the test framework
  utils/                  # Shared utilities (logging, exceptions, dates, push notifs, scheduler)
scripts/                  # User automation scripts (separate git repo, gitignored)
```

The `scripts/` directory is where all user automations live. It is a separate git repository, gitignored by the maestro repo, and loaded at runtime via `load_script_modules()`. Users import from maestro's public API (top-level packages only) to build their automations.

Public-facing packages (`domains/`, `triggers/`, `integrations/`, `utils/`, `testing/`) re-export their public API via `__init__.py` with `__all__` lists using `ClassName.__name__` references. Internal packages (`handlers/`, `registry/`) have empty `__init__.py`.

## Build / Lint / Test Commands

```bash
# Lint (ruff)
ruff check maestro                     # Lint the main package
ruff check --fix maestro               # Lint and auto-fix
ruff format maestro                    # Format code

# Type check (mypy) -- strict mode, all functions must be typed
mypy maestro

# Run all tests
pytest maestro

# Run a single test file
pytest maestro/testing/tests/test_entity_state.py

# Run a single test function
pytest maestro/testing/tests/test_entity_state.py::test_set_and_get_state

# Run tests with keyword match
pytest maestro -k "test_action"

# Deploy (Docker)
make deploy                            # Rebuild and restart all services
make build                             # Build Docker image only
make logs                              # View maestro container logs
make shell                             # Flask shell with pre-loaded imports
```

Tests use an in-memory SQLite database (overridden in `conftest.py`). No Redis or Home Assistant connection required.

## How Maestro Works

### Application Bootstrap (`app.py`)

`MaestroFlask` is a Flask subclass. Two module-level singletons are created at import time: `db = SQLAlchemy()` and `app = MaestroFlask(__name__)`. The constructor detects runtime mode and branches:

- **Test mode** (`"pytest" in sys.modules`): Initializes DB only. No WebSocket, no script loading, no scheduler jobs.
- **Shell mode** (Flask CLI `shell` command): Loads scripts and creates an idle scheduler. No WebSocket.
- **Production**: Full initialization sequence:
  1. `_initialize_db()` -- configures SQLAlchemy
  2. `load_script_modules()` -- imports all `scripts/**/*.py`, triggering decorator-based trigger registration
  3. `_initialize_scheduler()` -- creates `BackgroundScheduler` with `RedisJobStore`, registers cron and sun trigger jobs
  4. `_initialize_websocket()` -- starts `WebSocketManager` in a daemon thread
  5. Fires `MaestroEvent.STARTUP` triggers and registers `atexit` shutdown handlers

### Event Flow: WebSocket to User Script

The full path a Home Assistant event traverses:

1. **WebSocket** receives raw JSON from HA in a dedicated daemon thread with its own asyncio event loop
2. **`WebSocketManager._handle_event()`** classifies the event type, generates a process ID for log correlation, constructs a `WebSocketEvent` dataclass
3. **Handler dispatch** via `EventType` registry -- known events (`state_changed`, `ios.notification_action_fired`, etc.) get dedicated handlers; unknown events go to a default `event_fired` handler
4. **Handler** (e.g., `handle_state_changed`) parses event data into typed dataclasses (`StateChangeEvent`), caches new state via `StateManager`, and fires matching triggers
5. **`TriggerManager.fire_triggers()`** looks up registered functions by registry key (entity ID, event type, etc.), applies filters (from_state/to_state, user_id, etc.), and dispatches via `invoke_funcs_threaded()`
6. **Thread-per-trigger**: Each matching function runs in its own daemon thread with its own Flask `app_context()` (synchronous in tests via `invoke_funcs_sync()`)
7. **User script** executes, reading state via `Entity.state` / `EntityAttribute` (cache-through to Redis) and calling actions via `Entity.perform_action()` (REST API)

### State Management (`integrations/state_manager.py`)

`StateManager` is the central orchestrator, owning both a `HomeAssistantClient` (REST) and a `RedisClient` (cache). Key patterns:

- **Cache-through reads**: All state reads check Redis first; HA REST API is the fallback, which also populates the cache as a side effect
- **Event-driven cache writes**: WebSocket `state_changed` events trigger immediate cache updates via `cache_entity()`, which overwrites all state + attributes and deletes stale attribute keys
- **Type-preserving serialization**: Redis stores `{value, type}` JSON pairs so `int`, `float`, `bool`, `datetime`, `dict`, `list`, and `str` all round-trip correctly
- **Distributed locking**: Entity mutation operations (`patch_hass_entity`, `post_hass_entity`) acquire Redis locks to prevent concurrent modifications
- **Reconnection-aware sync**: If the WebSocket was disconnected for >30 minutes, a full REST API state sync runs on reconnect

In test mode, `StateManager.__init__()` auto-detects `test_mode_active()` and transparently swaps in `MockHomeAssistantClient` and `MockRedisClient`.

### Trigger System (`triggers/`)

#### Registration

Trigger decorators (`@state_change_trigger`, `@cron_trigger`, etc.) register functions into a class-level `_registry` at **import time**. The registry is a nested dict: `TriggerType -> registry_key -> list[TriggerRegistryEntry]`. Each entry contains the wrapped function, trigger args (for filtering), and a qualified name (for deduplication).

`load_script_modules()` imports all user scripts at startup, which executes decorator applications and populates the registry.

#### Decorator Pattern

All trigger decorators follow a three-layer structure:
1. **Outer function** -- receives configuration (entity IDs, cron fields, etc.)
2. **`decorator(func)`** -- builds a `TriggerRegistryEntry`, calls `XxxTriggerManager.register_function()`, returns wrapper
3. **`wrapper(*args)`** -- `@wraps(func)` proxy called at runtime

#### Optional Parameter Injection

`_invoke_func_with_param_handling()` uses `inspect.signature()` to match the decorated function's parameter names to available runtime params. This allows trigger functions to optionally accept context parameters or take no parameters at all:

```python
# Both are valid:
@state_change_trigger(switch.motion, to_state=ON)
def with_context(state_change: StateChangeEvent) -> None: ...

@state_change_trigger(switch.motion, to_state=ON)
def without_context() -> None: ...
```

#### Trigger Types

| Type | Registry Key | Filtering | Execution |
|------|-------------|-----------|-----------|
| `state_change` | entity ID | `from_state`, `to_state` exact match (None = wildcard) | Thread-per-trigger via `invoke_funcs_threaded` |
| `cron` | APScheduler `CronTrigger` object | None (APScheduler handles scheduling) | APScheduler's thread pool |
| `sun` | APScheduler `DateTrigger` object | None (self-rescheduling after each fire) | APScheduler's thread pool |
| `event_fired` | event type string | `user_id`, `**event_data` key-value match | Thread-per-trigger |
| `notif_action` | action name string | `device_id` | Thread-per-trigger |
| `maestro` | `MaestroEvent` enum | None | Threaded for STARTUP, synchronous for SHUTDOWN |
| `hass` | `HassEvent` enum | None | Thread-per-trigger |

Sun triggers are self-perpetuating: each fire computes the next solar event time from the `sun.sun` entity and schedules itself again, with a 20-hour guard to prevent rescheduling loops.

#### Test Registry

A separate `_test_registry` overlays the production `_registry`. Event-driven triggers use `get_registry(registry_union=True)` so both test-registered and production-registered triggers fire in tests.

### Entity System (`domains/`)

#### Entity Base Class (`entity.py`)

`Entity` is an ABC that all domain classes inherit from. Core behavior:

- **`state` property**: Reads from `StateManager.get_entity_state()` (cache-through). Setter is guarded by `allow_set_state` (only `True` for input_* domains and maestro).
- **`perform_action(action, **kwargs)`**: Calls `StateManager.hass_client.perform_action()`. Uses `@overload` with `Literal` for polymorphic return types (`response_expected=True` returns a dict).
- **`update(state, **attributes)`**: Delegates to `StateManager.patch_hass_entity()` for atomic read-modify-write.
- **Equality**: Uses identity comparison (`self is other`). Comparing an Entity to a non-Entity raises `TypeError` with a helpful hint ("Did you mean entity.state?").

Constants: `ON`, `OFF`, `HOME`, `AWAY`, `UNAVAILABLE`, `UNKNOWN`.

#### EntityAttribute Descriptor (`entity.py`)

A Python descriptor using PEP 695 generics (`EntityAttribute[T]`) constrained to `str | int | float | dict | list | bool | datetime`. Every attribute access is **live** -- it calls `StateManager.get_attribute_state()` each time (no local caching). Assignment delegates to `Entity.update()`.

#### Domain Subclasses

Each domain (Light, Switch, Climate, Cover, Lock, Fan, MediaPlayer, etc.) subclasses Entity, sets `domain = Domain.XXX`, and defines action methods that call `self.perform_action()`. Most set `allow_set_state = False`.

#### Custom Domain Subclasses (`scripts/custom_domains/`)

Users can extend built-in domain classes with device-specific or integration-specific functionality. Custom domains live in `scripts/custom_domains/` and are wildcard-imported into `maestro.domains` at the bottom of `domains/__init__.py`, making them available framework-wide.

The pattern for defining a custom domain:

```python
from maestro.domains.climate import Climate   # Direct module import (avoids circular import)

class Thermostat(Climate):
    class HVACMode(StrEnum):                  # Nested typed enums for modes/presets
        OFF = auto()
        HEAT = auto()

    @override
    def set_hvac_mode(self, mode: HVACMode) -> None:  # type:ignore[override]
        self.perform_action("set_hvac_mode", hvac_mode=mode)
```

Key details:
- Import from the **specific domain module** (`maestro.domains.climate`), not the package (`maestro.domains`), to avoid circular imports
- Use `@override` + `# type:ignore[override]` when narrowing parameter types from `str` to a specific `StrEnum`
- Export all custom domains via `__all__` in `scripts/custom_domains/__init__.py`
- When a custom domain is used as a HA action under a different HA domain (e.g., Sonos snapshot lives under the `sonos` domain, not `media_player`), call `self.state_manager.hass_client.perform_action()` directly with the correct `Domain` enum

Once defined, registry-generated entity classes automatically inherit from the custom subclass instead of the base domain class, and `RegistryManager` preserves the custom parent class during updates.

### Entity Registry (`registry/`)

`RegistryManager` auto-generates Python modules in `maestro/registry/` from Home Assistant entity data. Each domain gets a file (e.g., `registry/light.py`) containing:

- A **class per entity** that subclasses its domain class and declares `EntityAttribute` descriptors for each HA attribute
- A **module-level instance** instantiated with the entity ID string

```python
class LightMultiColorBulb(Light):
    brightness = EntityAttribute(int)
    rgb_color = EntityAttribute(list)
multi_color_bulb = LightMultiColorBulb("light.multi_color_bulb")
```

Registry modules are **code-generated and gitignored** -- never edit them manually (except `__init__.py` and `registry_manager.py`). When an entity already inherits from a custom domain subclass, the manager preserves that parent class during updates.

### WebSocket System (`integrations/home_assistant/`)

- **`WebSocketClient`**: Async aiohttp-based client. Connects, authenticates with a long-lived token, subscribes to all HA events, and runs a listener loop that invokes a callback per event.
- **`WebSocketManager`**: Lifecycle orchestrator running in a daemon thread with its own asyncio event loop. Handles reconnection with linear backoff (2s increments, max 30s), state sync on reconnect, and event routing to handlers.

### Redis Client (`integrations/redis.py`)

Colon-delimited key structure with three prefixes: `STATE:` (entity/attribute cache, 1-week TTL), `REGISTERED:` (registry tracking), `ENTITY_LOCK:` (distributed locks). Values are JSON-encoded with type metadata for lossless round-trips. Uses `SCAN` (not `KEYS`) for pattern matching.

### Utilities (`utils/`)

- **Logging** (`logging.py`): `LoggerProxy` singleton bound to `log`. Every log line carries a `process_id` context variable for correlating event processing chains across threads. Always use structured key-value arguments, never string interpolation.
- **Exceptions** (`exceptions.py`): Clean hierarchy with compact `class XxxError(BaseError): ...` syntax. Groups: configuration, HA client, entity, trigger, and test framework errors.
- **Dates** (`dates.py`): `local_now()`, `resolve_timestamp()`, `format_duration()`, `IntervalSeconds` IntEnum for TTL constants.
- **Scheduler** (`scheduler.py`): `JobScheduler` wraps APScheduler for one-shot scheduled jobs. Auto-redirects to `MockJobScheduler` in tests.
- **Push** (`push.py`): `Notif` class for iOS push notifications via HA. Supports priorities, actionable buttons, custom sounds, grouping/tagging.

### Testing Framework (`testing/`)

- **`MaestroTest`** (`maestro_test.py`): The primary test interface, injected as the `mt` fixture. Provides methods for state setup, trigger simulation, action assertions, entity assertions, job scheduler assertions, and time mocking (via freezegun).
- **Mocks** (`mocks.py`): `MockHomeAssistantClient` (in-memory entity store + action call recording), `MockRedisClient` (in-memory dict), `MockJobScheduler` (stores jobs without executing). All extend real client classes with `@override`.
- **Context** (`context.py`): Per-test global singletons (`_test_state_manager`, `_test_job_scheduler`) with lazy init and full reset between tests.
- **Fixtures** (`fixtures.py`): The `mt` fixture creates a lightweight Flask app (not `MaestroFlask`) with in-memory SQLite, yields a `MaestroTest` instance, then tears down DB and resets test context.

Tests execute synchronously because `invoke_funcs_threaded()` detects test mode and delegates to `invoke_funcs_sync()`.

## Code Style

### Formatting

- **Line length**: 100 characters (configured in `ruff.toml`)
- **Formatter**: Ruff (`ruff format`), applied on save
- **Final newline**: Always required
- **No print statements**: Enforced by ruff rule `T20` -- use `log` instead
- **No `os.path`**: Enforced by ruff rule `PTH` -- use `pathlib`

### Imports

Three groups separated by blank lines, each alphabetically sorted (enforced by ruff isort):

```python
import re                                                    # 1. stdlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, final

from apscheduler.triggers.cron import CronTrigger            # 2. third-party

from maestro.triggers.types import TriggerFuncParamsT        # 3. local
from maestro.utils.logging import log
```

Use `TYPE_CHECKING` guard to avoid circular imports:

```python
if TYPE_CHECKING:
    from maestro.app import MaestroFlask
```

Use `# type:ignore[import-untyped]` on untyped third-party imports.

### Type Annotations

- **Every function must have full type annotations** including return type (enforced by mypy `disallow_untyped_defs`)
- Always annotate `-> None` for void functions
- Use `X | None` instead of `Optional[X]`
- Use `collections.abc.Callable` / `collections.abc.Mapping` instead of `typing.Callable` / `typing.Mapping`
- Use Python 3.12+ generic syntax: `class Entity[T]:`
- Use `TypedDict` for structured parameter dicts
- Use `@overload` with `Literal` for polymorphic return types
- Use `@override` on overridden methods (especially in mocks)
- Type aliases use PascalCase with `T` suffix: `CachedValueT`, `TriggerFuncParamsT`

### Naming Conventions

| Kind | Convention | Examples |
|---|---|---|
| Functions/methods | `snake_case` | `fire_triggers`, `get_entity_state` |
| Private methods | `_snake_case` | `_initialize_db`, `_run_event_loop` |
| Unused params | `_prefixed` | `_event: WebSocketEvent`, `_logger` |
| Classes | `PascalCase` | `StateManager`, `MaestroTest` |
| Manager classes | `XxxManager` suffix | `TriggerManager`, `RegistryManager` |
| Mock classes | `MockXxx` prefix | `MockHomeAssistantClient` |
| Constants | `SCREAMING_SNAKE_CASE` | `ON`, `OFF`, `HOME`, `SCHEDULER_JOB_PREFIX` |
| Enums | `PascalCase` class, `SCREAMING_SNAKE_CASE` members | `TriggerType.STATE_CHANGE` |
| Type aliases | `PascalCaseT` | `CachedValueT`, `RegistryT` |

### Enums

Use `StrEnum` with `auto()` for string enums (produces lowercase values). Use `IntEnum` for numeric constants:

```python
class Domain(StrEnum):
    LIGHT = auto()           # "light"
    MEDIA_PLAYER = auto()    # "media_player"
```

### Custom String Types

Subclass `str` with `__new__` for validated identifiers (not `NewType`):

```python
class StateId(str):
    def __new__(cls, value: str) -> "StateId":
        if not re.match(cls.entity_pattern, value):
            raise ValueError(f"Invalid format: {value}")
        return str.__new__(cls, value)
```

### Error Handling

- Custom exception hierarchy in `maestro/utils/exceptions.py` with compact `class XxxError(BaseError): ...` syntax
- Always chain exceptions with `from e`: `raise MalformedResponseError("msg") from e`
- Use `contextlib.suppress(XxxError)` instead of bare `try/except` for expected exceptions
- Use `log.exception(...)` at thread/background-task boundaries for unexpected errors

### Logging

Single `log` instance imported everywhere from `maestro.utils.logging`. Always use structured key-value arguments -- never string interpolation in log messages:

```python
from maestro.utils.logging import log

log.info("Registered trigger", function_name=func.__name__, trigger_type=trigger_type)
log.debug("Processing state change", entity_id=entity_id, old_state=old, new_state=new)
log.exception("Failed to load module", module=module_name)
```

### Docstrings

Short imperative sentences. No Google/numpy `Args:`/`Returns:` sections. Multi-line only when explaining complex behavior:

```python
def cache_entity(self, entity_data: EntityData) -> None:
    """Overwrite an entity's state and attributes, removing any stale attributes"""
```

Use `# MARK:` comments to organize logical groups of methods within large classes.

### Dataclasses

Use `@dataclass` for value/data transfer objects. Use `__post_init__` for data sanitization.

## Testing Conventions

- **Framework**: pytest with custom `MaestroTest` fixture
- **Test files**: Named `test_*.py`, module-level docstring describing scope
- **Test functions**: Named `test_*`, short one-line docstrings, return type `-> None`
- **No test classes** -- all tests are module-level functions
- **First parameter**: Always `mt: MaestroTest` (provides clean test context per test)
- **Pattern**: Setup state -> trigger action -> assert results

```python
def test_motion_turns_on_light(mt: MaestroTest) -> None:
    """Test that motion sensor triggers bedroom light"""
    mt.set_state(switch.motion_sensor, OFF)
    mt.trigger_state_change(switch.motion_sensor, old=OFF, new=ON)
    mt.assert_action_called("light", "turn_on", entity_id="light.bedroom")
```
