# Maestro

Strongly-typed Python automation framework for Home Assistant. Flask + SQLAlchemy + Redis + APScheduler + structlog. Runs in Docker, connects to Home Assistant via WebSocket and REST API. Python 3.13+.

## Project Structure

```
maestro/                  # Main package
  app.py                  # Flask app factory, db/app singletons
  config.py               # All env-var configuration (flat module)
  domains/                # Entity domain classes (Light, Switch, Climate, etc.)
  handlers/               # WebSocket event handler functions
  integrations/           # External service clients (HA REST, WebSocket, Redis, StateManager)
  triggers/               # Decorator-based trigger system (state_change, cron, sun, etc.)
  registry/               # Auto-generated entity registry (code-generated, relaxed linting)
  testing/                # Test framework (MaestroTest, mocks, fixtures)
    tests/                # Self-tests for the test framework
  utils/                  # Shared utilities (logging, exceptions, dates, push notifs, scheduler)
scripts/                  # User automation scripts (separate git repo, gitignored)
```

Public-facing packages (`domains/`, `triggers/`, `integrations/`, `utils/`, `testing/`) re-export their public API via `__init__.py` with `__all__` lists. Internal packages (`handlers/`, `registry/`) have empty `__init__.py`.

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

| Kind              | Convention                                         | Examples                                    |
| ----------------- | -------------------------------------------------- | ------------------------------------------- |
| Functions/methods | `snake_case`                                       | `fire_triggers`, `get_entity_state`         |
| Private methods   | `_snake_case`                                      | `_initialize_db`, `_run_event_loop`         |
| Unused params     | `_prefixed`                                        | `_event: WebSocketEvent`, `_logger`         |
| Classes           | `PascalCase`                                       | `StateManager`, `MaestroTest`               |
| Manager classes   | `XxxManager` suffix                                | `TriggerManager`, `RegistryManager`         |
| Mock classes      | `MockXxx` prefix                                   | `MockHomeAssistantClient`                   |
| Constants         | `SCREAMING_SNAKE_CASE`                             | `ON`, `OFF`, `HOME`, `SCHEDULER_JOB_PREFIX` |
| Enums             | `PascalCase` class, `SCREAMING_SNAKE_CASE` members | `TriggerType.STATE_CHANGE`                  |
| Type aliases      | `PascalCaseT`                                      | `CachedValueT`, `RegistryT`                 |

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

### Dataclasses

Use `@dataclass` for value/data transfer objects.

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

## Architecture Notes

- **Trigger registration at import time** via decorators (`@state_change_trigger`, `@cron_trigger`, etc.)
- **Thread-per-trigger execution** in production; synchronous in tests
- **Registry modules are code-generated** by `RegistryManager` -- do not edit `maestro/registry/*.py` files (except `__init__.py` and `registry_manager.py`)
- **Singleton pattern** for `db` and `app` in `app.py`
- **Lazy initialization** throughout -- test/shell modes detected at runtime
- **`scripts/` is a separate git repo** loaded at runtime; import from it as `from scripts.xxx import ...`
- User-facing imports should come from top-level packages only (e.g., `from maestro.triggers import state_change_trigger`, never from deeper submodules)
