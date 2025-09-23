# Registry

The registry contains auto-generated domain modules that provide strongly-typed access to Home Assistant entities and their attributes. Each module corresponds to a specific entity domain (e.g., `light`, `switch`, `sensor`) and contains entity instances that can be used throughout the codebase.

## How It Works

- **Programmatic Updates**: Each module is automatically updated and should be edited with caution
- **Module Parsing**: Line-by-line formatting is critical in parsing and editing registry modules; avoid altering the format
- **Domain Subclassing**: Parent domain classes can be replaced by subclasses (e.g., `SomeCarClimate(TeslaClimate)` instead of `SomeCarClimate(Climate)`)
- **Disaster Recovery**: Deleting a registry entity (or entire module) and allowing it to recreate should fix most problems

These registry entities provide type-safe access to Home Assistant entities with full IDE support and autocomplete functionality.
