# Maestro Core System

This directory contains the core Maestro middleware system that bridges Home Assistant with Python automation scripts. If you're writing automations, see the [scripts README](../scripts/README.md) instead.

## Architecture Overview

Maestro consists of four main subsystems:

### 🌐 **Flask API Server** (`app.py`)
- Receives Home Assistant state change webhooks
- Provides health check and testing endpoints  
- Handles request routing and logging

### 🏠 **Home Assistant Integration** (`integrations/home_assistant/`)
- **Client** - Full REST API integration for bidirectional communication
- **Types** - Strongly typed data models (EntityId, StateChangeEvent, etc.)
- **Entity abstraction** - Object-oriented interfaces for HA entities

### ⚡ **Redis Cache Layer** (`integrations/redis.py`, `integrations/state_manager.py`)
- High-performance entity state storage with type preservation
- Intelligent caching with 30-day TTL and selective attribute storage
- Real-time cache updates from state change webhooks

### 🎯 **Trigger System** (`triggers/`)
- Decorator-based event handling (`@state_change_trigger`)
- Registry system for routing state changes to user functions
- Intelligent parameter injection with error handling

## Core Data Flow

```
Home Assistant State Change
        ↓ (webhook)
Flask App (routes/state_changed.py)
        ↓ (creates StateChangeEvent)
StateManager.cache_state_change()
        ↓ (updates Redis cache)
StateChangeTriggerManager.execute_triggers()
        ↓ (finds registered functions)
User Scripts (@state_change_trigger functions)
        ↓ (can interact with entities via)
Entity Classes (Switch, Climate, etc.)
        ↓ (use StateManager + HomeAssistantClient)
Home Assistant REST API
```

## Key Components

### State Management

The `StateManager` class orchestrates all data flow:

```python
# Caching with type preservation
state_manager.set_cached_state(entity_id, "on")  # string
state_manager.set_cached_state(attribute_id, 72.5)  # float preserved

# Fetching fresh data
entity_response = state_manager.fetch_hass_entity("switch.living_room")
```

### Trigger System

The trigger system enables event-driven automation:

```python
# Registration happens automatically with decorators
@state_change_trigger("switch.bedroom_light")
def my_automation(state_change: StateChangeEvent):
    # Function gets registered for this entity
    # Called automatically when switch.bedroom_light changes
    pass
```

### Entity Types

Typed entity classes provide OOP interfaces:

- `Switch` - Binary switches with on/off/toggle actions
- `Climate` - HVAC systems with temperature and fan controls  
- `Calendar` - Calendar entities (basic support)

## Development Setup

### Prerequisites

- Python 3.12+
- Docker & Docker Compose (for Redis)
- Home Assistant instance with REST API access

### Local Development

```bash
# Build the Docker image
make build

# Start services (including Redis)
docker-compose up -d

# Run tests
make test

# Run specific tests
make test TEST=maestro/tests/test_specific_file.py

# Open interactive Flask shell with pre-loaded imports
make shell

# Open bash shell in container for debugging
make bash
```

### Environment Variables

Create a `.env` file in the project root:

```bash
HOME_ASSISTANT_URL=http://your-hass-ip:8123
HOME_ASSISTANT_TOKEN=your-long-lived-access-token
REDIS_HOST=redis  # Docker service name
REDIS_PORT=6379
NGINX_TOKEN=your-secure-token
```

## Testing

### Test Structure

- `tests/` - Core system tests
- `integrations/tests/` - Integration layer tests
- Registry isolation prevents test pollution

### Running Tests

```bash
# All tests
make test

# Specific test file
make test TEST=maestro/tests/test_trigger_manager.py

# Specific test method
make test TEST=maestro/tests/test_trigger_manager.py::TestTriggerManager::test_register_function
```

### Test Registry System

Tests use isolated registries to prevent cross-test pollution:

```python
# In test setup
TriggerManager._test_registry = initialize_trigger_registry()

# Tests run in isolation using test registry
# Production registry remains unaffected
```

## API Endpoints

- `GET /` - Health check endpoint
- `POST /events/state-changed` - Webhook for Home Assistant state changes

## Database Schema (Redis)

Maestro uses Redis with structured keys:

```
STATE:domain:entity          # Entity state (e.g., "on")
STATE:domain:entity:attr     # Entity attributes (type-preserved)
```

Examples:
- `STATE:switch:living_room` → `"on"` (string)
- `STATE:sensor:temperature` → `"72.5"` (stored as float)
- `STATE:climate:thermostat:current_temperature` → `72.5` (float)

## Contributing

### Code Organization

- Keep integrations modular and testable
- Use type hints everywhere
- Follow the existing patterns for new entity types
- Add comprehensive tests for new features

### Adding New Entity Types

1. Create entity class in `domains/`
2. Add domain to `Domain` enum in `integrations/home_assistant/types.py`
3. Export in `maestro/__init__.py` if commonly used
4. Add tests in `tests/`

### Adding New Trigger Types

1. Create new trigger params class in `triggers/trigger_manager.py`
2. Add to `WrappedFuncParamsT` union type
3. Create manager class extending `TriggerManager`
4. Create decorator function
5. Export in `triggers/__init__.py`

## Architecture Decisions

### Why Redis?
- Type preservation with JSON serialization
- High performance for frequent state lookups
- Built-in TTL for automatic cleanup
- Horizontal scaling potential

### Why Flask?
- Lightweight for webhook receiving
- Excellent ecosystem for REST APIs
- Simple deployment with gunicorn
- Good testing support

### Why Decorator-Based Triggers?
- Declarative and intuitive for users
- Automatic registration at import time
- Clean separation of concerns
- Easy to test and debug

This system provides the foundation for Python-based Home Assistant automation while maintaining clean architecture, strong typing, and excellent testability.