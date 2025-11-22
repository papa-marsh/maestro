"""Mock Home Assistant client for testing without a real Home Assistant instance."""

from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from typing import Any

from maestro.integrations.home_assistant.domain import Domain
from maestro.integrations.home_assistant.types import EntityData, EntityId
from maestro.utils.dates import local_now


@dataclass
class ActionCall:
    """Records a single action/service call made to Home Assistant."""

    domain: Domain
    action: str
    entity_id: str | list[str] | None
    params: dict[str, Any]
    timestamp: datetime = field(default_factory=local_now)


class MockHomeAssistantClient:
    """In-memory mock of HomeAssistantClient for testing without Home Assistant."""

    def __init__(self) -> None:
        self._entities: dict[str, EntityData] = {}
        self._action_calls: list[ActionCall] = []

    def check_health(self) -> bool:
        """Always returns True for mock client."""
        return True

    def get_entity(self, entity_id: str) -> EntityData:
        """Get an entity from the mock store."""
        if entity_id not in self._entities:
            raise ValueError(f"Entity {entity_id} doesn't exist")
        return self._entities[entity_id]

    def get_all_entities(self) -> list[EntityData]:
        """Get all entities from the mock store."""
        return list(self._entities.values())

    def set_entity(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any],
    ) -> tuple[EntityData, bool]:
        """Set an entity's state and attributes in the mock store."""
        created = entity_id not in self._entities

        # Add standard attributes if not present
        if "last_changed" not in attributes:
            attributes["last_changed"] = local_now()
        if "last_reported" not in attributes:
            attributes["last_reported"] = local_now()
        if "last_updated" not in attributes:
            attributes["last_updated"] = local_now()

        entity_data = EntityData(
            entity_id=EntityId(entity_id),
            state=state,
            attributes=attributes.copy(),
        )
        self._entities[entity_id] = entity_data

        return entity_data, created

    def delete_entity(self, entity_id: str) -> None:
        """Delete an entity from the mock store."""
        if entity_id not in self._entities:
            raise ValueError(f"Entity {entity_id} doesn't exist")
        del self._entities[entity_id]

    def delete_entity_if_exists(self, entity_id: str) -> None:
        """Delete an entity if it exists, ignoring errors if it doesn't."""
        if entity_id in self._entities:
            del self._entities[entity_id]

    def perform_action(
        self,
        domain: Domain,
        action: str,
        entity_id: str | list[str] | None = None,
        **body_params: Any,
    ) -> list[EntityData]:
        """Record an action call and optionally update entity state."""
        # Record the action call
        action_call = ActionCall(
            domain=domain,
            action=action,
            entity_id=entity_id,
            params=body_params,
        )
        self._action_calls.append(action_call)

        # Simulate common state changes for known actions
        entities_to_return: list[EntityData] = []

        if entity_id is not None:
            entity_ids = [entity_id] if isinstance(entity_id, str) else entity_id

            for eid in entity_ids:
                if eid in self._entities:
                    entity = self._entities[eid]

                    # Simulate state changes for common actions
                    if action == "turn_on" and entity.state == "off":
                        entity.state = "on"
                        entity.attributes["last_updated"] = local_now()
                    elif action == "turn_off" and entity.state == "on":
                        entity.state = "off"
                        entity.attributes["last_updated"] = local_now()
                    elif action == "toggle":
                        entity.state = "off" if entity.state == "on" else "on"
                        entity.attributes["last_updated"] = local_now()

                    entities_to_return.append(entity)

        return entities_to_return

    def execute_request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
    ) -> tuple[dict | list, int]:
        """Mock method for direct API requests - not typically used in tests."""
        return {}, HTTPStatus.OK

    def get_action_calls(self) -> list[ActionCall]:
        """Get all recorded action calls for assertions."""
        return self._action_calls.copy()

    def get_action_calls_for_entity(self, entity_id: str) -> list[ActionCall]:
        """Get action calls for a specific entity."""
        return [
            call
            for call in self._action_calls
            if call.entity_id == entity_id
            or (isinstance(call.entity_id, list) and entity_id in call.entity_id)
        ]

    def get_action_calls_for_domain_action(
        self, domain: Domain, action: str
    ) -> list[ActionCall]:
        """Get action calls for a specific domain and action."""
        return [
            call
            for call in self._action_calls
            if call.domain == domain and call.action == action
        ]

    def clear_action_calls(self) -> None:
        """Clear recorded action calls. Useful between test steps."""
        self._action_calls.clear()

    def clear_entities(self) -> None:
        """Clear all entities from mock store."""
        self._entities.clear()

    def clear_all(self) -> None:
        """Clear all mock data."""
        self.clear_entities()
        self.clear_action_calls()

    def add_test_entity(
        self,
        entity_id: str,
        state: str = "off",
        attributes: dict[str, Any] | None = None,
    ) -> EntityData:
        """Helper to add a test entity to the mock store."""
        attrs = attributes or {}
        entity_data, _ = self.set_entity(entity_id, state, attrs)
        return entity_data
