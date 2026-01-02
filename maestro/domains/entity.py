from abc import ABC
from datetime import datetime
from typing import Any, Literal, cast, overload

from maestro.integrations.home_assistant.domain import Domain
from maestro.integrations.home_assistant.types import AttributeId, EntityId
from maestro.integrations.state_manager import StateManager
from maestro.utils.exceptions import (
    EntityConfigurationError,
    EntityOperationError,
    MalformedResponseError,
    MockEntityDoesNotExistError,
    StateOverwriteNotAllowedError,
    UnitTestFrameworkError,
)
from maestro.utils.internal import test_mode_active

ON = "on"
OFF = "off"
HOME = "home"
AWAY = "not_home"
UNAVAILABLE = "unavailable"


class EntityAttribute[T: (str, int, float, dict, list, bool, datetime)]:
    def __init__(self, attribute_type: type[T]) -> None:
        self.attribute_type: type[T] = attribute_type

    def __set_name__(self, owner: type["Entity"], name: str) -> None:
        self.name = name

    def __get__(self, obj: "Entity", objtype: type["Entity"] | None = None) -> T:
        attribute_id = AttributeId(f"{obj.id}.{self.name}")
        try:
            value = obj.state_manager.get_attribute_state(
                attribute_id=attribute_id,
                expected_type=self.attribute_type,
            )
        except MockEntityDoesNotExistError:
            value = self._build_default_test_value()

        return cast(T, value)

    def __set__(self, obj: "Entity", value: T) -> None:
        entity_response = obj.state_manager.fetch_hass_entity(obj.id)

        entity_response.attributes[self.name] = value
        entity_data, _ = obj.state_manager.hass_client.set_entity(
            entity_id=obj.id,
            state=entity_response.state,
            attributes=entity_response.attributes,
        )
        obj.state_manager.cache_entity(entity_data)

    def _build_default_test_value(self) -> T:
        """Used only during test mode to generate placeholder attribute values"""
        if not test_mode_active():
            raise UnitTestFrameworkError("Mock state manager found outside of test mode")
        from maestro.testing.mocks import mock_attribute_default_value_map

        return cast(T, mock_attribute_default_value_map[self.attribute_type](self.name))


class Entity(ABC):
    domain: Domain
    allow_set_state: bool = True

    id: EntityId

    friendly_name = EntityAttribute(str)
    last_changed = EntityAttribute(datetime)
    last_updated = EntityAttribute(datetime)
    previous_state = EntityAttribute(str)

    def __init__(
        self,
        entity_id: str | EntityId,
        state_manager: StateManager | None = None,
    ) -> None:
        self.id = EntityId(entity_id) if isinstance(entity_id, str) else entity_id
        self._state_manager = state_manager

        valid_classes = {c.__name__ for c in type(self).__mro__ if c not in [Entity, ABC, object]}
        if self.id.domain_class_name not in valid_classes:
            raise EntityConfigurationError("Mismatch between entity domain and domain class")

    def __getstate__(self) -> dict[str, Any]:
        """Exclude _state_manager from pickling to avoid serializing locks"""
        state = self.__dict__.copy()
        state["_state_manager"] = None
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore instance from pickled state, allowing lazy re-init of state_manager"""
        self.__dict__.update(state)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            other_type = type(other).__name__
            raise TypeError(f"Can't compare Entity to {other_type}. Did you mean {self.id}.state?")
        return self is other

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            other_type = type(other).__name__
            raise TypeError(f"Can't compare Entity to {other_type}. Did you mean {self.id}.state?")
        return self is not other

    def __hash__(self) -> int:
        return object.__hash__(self)

    @property
    def state_manager(self) -> StateManager:
        """Lazy load the state manager for this entity"""
        if test_mode_active():
            return StateManager()

        self._state_manager = self._state_manager or StateManager()
        return self._state_manager

    @property
    def state(self) -> str:
        """Get the current state of the entity (always a string)"""
        return self.state_manager.get_entity_state(self.id)

    @state.setter
    def state(self, value: str) -> None:
        """Set the state of the entity"""
        if not self.allow_set_state:
            raise StateOverwriteNotAllowedError(f"Cannot set state for {self.domain} entities")
        if not isinstance(value, str):
            raise TypeError(f"Expected string but got `{value}` of type `{type(value).__name__}`")

        entity_response = self.state_manager.fetch_hass_entity(self.id)

        entity_response.state = value
        entity_data, _ = self.state_manager.hass_client.set_entity(
            entity_id=self.id,
            state=entity_response.state,
            attributes=entity_response.attributes,
        )
        self.state_manager.cache_entity(entity_data)

    @overload
    def perform_action(
        self,
        action: str,
        response_expected: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]: ...

    @overload
    def perform_action(
        self,
        action: str,
        response_expected: Literal[False] = False,
        **kwargs: Any,
    ) -> None: ...

    def perform_action(
        self,
        action: str,
        response_expected: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Perform an action related to the entity"""
        changed_states, action_response = self.state_manager.hass_client.perform_action(
            domain=self.id.domain,
            action=action,
            entity_id=self.id,
            response_expected=response_expected,
            **kwargs,
        )
        if len(changed_states) > 1:
            raise MalformedResponseError("Received more than one EntityData from action call")
        if response_expected and not action_response:
            raise EntityOperationError("Did not receive action response where one was expected")

        return action_response
