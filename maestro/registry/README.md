# Registry

The registry contains auto-generated domain modules that provide strongly-typed access to Home Assistant entities and their attributes. Each module corresponds to a specific entity domain (e.g., `light`, `switch`, `sensor`) and contains entity instances that can be used throughout the codebase.

## How It Works

- **Programmatic Updates**: Each module is automatically generated and updated by `RegistryManager` -- edit with caution
- **Module Parsing**: Line-by-line formatting is critical for parsing and editing registry modules; do not alter the format
- **Disaster Recovery**: Deleting a registry entity (or entire module) and allowing it to recreate should fix most problems
- **Gitignored**: All generated modules are gitignored. Only `__init__.py`, `registry_manager.py`, and this `README.md` are tracked

## Generated Module Structure

Each generated module contains one class per entity (subclassing the appropriate domain class) with `EntityAttribute` descriptors, plus a module-level instance:

```python
# maestro/registry/light.py (auto-generated)

from maestro.domains import Light  # type:ignore[attr-defined, unused-ignore]
from maestro.domains.entity import EntityAttribute
from datetime import datetime

class LightMultiColorBulb(Light):
    brightness = EntityAttribute(int)
    rgb_color = EntityAttribute(list)
    color_mode = EntityAttribute(str)
multi_color_bulb = LightMultiColorBulb("light.multi_color_bulb")
```

## Custom Domain Subclasses

Registry superclasses can be overridden with custom domain subclasses for extended functionality. Custom subclassing is respected by `RegistryManager`'s upsert logic, provided the format of the registry module is kept intact.

Note in the example that `ClimateBathroomFloorThermostat` inherits from `BathroomFloor` (which itself inherits from `Climate`):

```python
# maestro/registry/climate.py (auto-generated)

from maestro.domains import BathroomFloor, Climate  # type:ignore[attr-defined, unused-ignore]
...

class ClimateBathroomFloorThermostat(BathroomFloor):
    ...
bathroom_floor_thermostat = ClimateBathroomFloorThermostat("climate.bathroom_floor_thermostat")
```

### Setting Up Custom Domains

Custom domain classes must be defined in `scripts/custom_domains/` and exported via `__all__`:

```python
# scripts/custom_domains/__init__.py
from .climate import BathroomFloor, TeslaHVAC, Thermostat
from .sonos_speaker import SonosSpeaker

__all__ = [
    BathroomFloor.__name__,
    TeslaHVAC.__name__,
    Thermostat.__name__,
    SonosSpeaker.__name__,
]
```

They are wildcard-imported into `maestro.domains` at startup, which makes them available to the registry's import statements. See the main README for full custom domain documentation.
