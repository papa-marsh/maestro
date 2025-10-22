# Registry

The registry contains auto-generated domain modules that provide strongly-typed access to Home Assistant entities and their attributes. Each module corresponds to a specific entity domain (e.g., `light`, `switch`, `sensor`) and contains entity instances that can be used throughout the codebase.

## How It Works

- **Programmatic Updates**: Each module is automatically updated and should be edited with caution
- **Module Parsing**: Line-by-line formatting is critical in parsing and editing registry modules; avoid altering the format
- **Disaster Recovery**: Deleting a registry entity (or entire module) and allowing it to recreate should fix most problems

These registry entities provide type-safe access to Home Assistant entities with full IDE support and autocomplete functionality.

## Domain Subclasses

Registry superclasses can be overridden with custom domain subclasses for extended functionality. Custom subclassing is respected by the registry manager's upsert logic, provided the format of the registry module is kept intact.

Note in the example that `ClimateBathroomFloorThermostat` inherits from `BathroomFloor` (which itself inherits from `Climate`)

```python
# maestro/registry/climate.py

...
from maestro.domains import BathroomFloor, Climate  # type:ignore[attr-defined, unused-ignore]
...
class ClimateBathroomFloorThermostat(BathroomFloor):
    ...
bathroom_floor_thermostat = ClimateBathroomFloorThermostat("climate.bathroom_floor_thermostat")
```

### Import Structure

**Note:** Custom domain classes must be exported from `scripts.custom_domains`.

```python
# scripts/custom_domains/__init__.py

from .climate import BathroomFloor, TeslaHVAC, Thermostat
from .media_player import SonosSpeaker

__all__ = [
    "BathroomFloor",
    "TeslaHVAC",
    "Thermostat",
    "SonosSpeaker",
]

```

### Example 1: Extended Action Methods

While all `media_player` entities share the same base actions (e.g., `media_player.play`), the Sonos integration also exposes actions like `sonos.join` and `sonos.snapshot`.

```python
# scripts/custom_domains/media_player.py

from maestro.domains.media_player import MediaPlayer
from maestro.integrations.home_assistant.domain import Domain
from maestro.integrations.home_assistant.types import EntityId


class SonosSpeaker(MediaPlayer):
    def join(self, members: list[EntityId]) -> None:
        self.perform_action("join", group_members=members)

    def unjoin(self) -> None:
        self.perform_action("unjoin")

    def snapshot(self, with_group: bool = False) -> None:
        self.state_manager.hass_client.perform_action(
            domain=Domain.SONOS,
            action="snapshot",
            entity_id=self.id,
            with_group=with_group,
        )

    def restore(self, with_group: bool = False) -> None:
        self.state_manager.hass_client.perform_action(
            domain=Domain.SONOS,
            action="restore",
            entity_id=self.id,
            with_group=with_group,
        )
```

### Example 2: Attribute Value Enums

Add type safety and autocomplete when passing argument values.

```python
# scripts/custom_domains/climate.py

from enum import StrEnum, auto
from typing import override

from maestro.domains.climate import Climate


class TeslaHVAC(Climate):
    class HVACMode(StrEnum):
        OFF = auto()
        HEAT_COOL = auto()

    class FanMode(StrEnum):
        OFF = auto()
        BIOWEAPON = auto()

    class PresetMode(StrEnum):
        NORMAL = auto()
        DEFROST = auto()
        KEEP = auto()
        DOG = auto()
        CAMP = auto()

    @override
    def set_fan_mode(self, mode: FanMode) -> None:
        self.perform_action("set_fan_mode", mode=mode)

    @override
    def set_hvac_mode(self, mode: HVACMode) -> None:
        self.perform_action("set_hvac_mode", mode=mode)

    @override
    def set_preset_mode(self, mode: PresetMode) -> None:
        self.perform_action("set_preset_mode", mode=mode)
```
