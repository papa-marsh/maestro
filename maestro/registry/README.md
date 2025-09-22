# Registry

The registry contains auto-generated entity modules that provide strongly-typed access to Home Assistant entities. Each module corresponds to a specific entity domain (e.g., `light`, `switch`, `sensor`) and contains entity instances that can be used throughout the codebase.

## How It Works

- **Programmatic Updates**: Each module is automatically updated and should be edited with caution
- **One Entity Per Line**: Each entity must exist on exactly one line for proper parsing
- **Domain Subclassing**: Base domain classes can be replaced by subclasses (e.g., `TeslaClimate(<car_entity>)` instead of `Climate(<car_entity>)`)
- **Selective Usage**: Comment out unused entities to remove them from IDE autocomplete

## Example

```python
# maestro/registry/light.py
from maestro.domains import Light

multi_color_bulb = Light("light.multi_color_bulb")
outside_light = HueLight("light.outside_light")
```

These registry entities provide type-safe access to Home Assistant entities with full IDE support and autocomplete functionality.
