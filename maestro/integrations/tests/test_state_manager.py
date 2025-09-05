import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from maestro.integrations.home_assistant import StateChangeEvent
from maestro.integrations.redis import RedisClient
from maestro.integrations.state_manager import STATE_CACHE_PREFIX, CachedState, StateManager
from maestro.utils.dates import utc_now


class TestStateManagerIntegration:
    @pytest.fixture(scope="class")
    def state_manager(self) -> StateManager:
        return StateManager()

    @pytest.fixture(scope="class", autouse=True)
    def check_services_health_or_skip(self, state_manager: StateManager) -> None:
        """Check both Home Assistant and Redis health before running tests"""
        if not state_manager.hass_client.check_health():
            pytest.skip("Home Assistant is not healthy - skipping integration tests")
        if not state_manager.redis_client.check_health():
            pytest.skip("Redis is not healthy - skipping integration tests")

    def test_fetch_hass_entity(self, state_manager: StateManager) -> None:
        """Test fetching entity from Home Assistant and caching it"""
        test_entity_id = "maestro.unit_test"

        # Ensure test entity exists in Home Assistant
        state_manager.hass_client.set_entity(
            entity_id=test_entity_id,
            state="test_state",
            attributes={"friendly_name": "Unit Test Entity", "test_attr": "test_value"},
        )

        # Clean up any existing cached data for this entity
        redis_key_prefix = f"{STATE_CACHE_PREFIX}:{test_entity_id.replace('.', ':')}"
        cached_keys = state_manager.redis_client.get_keys(f"{redis_key_prefix}*")
        if cached_keys:
            state_manager.redis_client.delete(*cached_keys)

        # Fetch entity from Home Assistant
        entity_response = state_manager.fetch_hass_entity(test_entity_id)

        # Verify we got a valid entity response
        assert entity_response is not None
        assert entity_response.entity_id == test_entity_id
        assert isinstance(entity_response.state, str)
        assert isinstance(entity_response.attributes, dict)

        # Verify the entity state was cached
        cached_state = state_manager.get_cached_state(test_entity_id)
        assert cached_state == entity_response.state

        # Verify some attributes were cached (excluding ignored ones)
        cached_last_updated = state_manager.get_cached_state(f"{test_entity_id}.last_updated")
        assert cached_last_updated is not None
        assert isinstance(cached_last_updated, datetime)

        cached_test_attr = state_manager.get_cached_state(f"{test_entity_id}.test_attr")
        assert cached_test_attr == "test_value"

        # Clean up test entity
        state_manager.hass_client.delete_entity_if_exists(test_entity_id)

    def test_cache_state_change(self, state_manager: StateManager) -> None:
        """Test caching a state change event"""
        test_entity_id = "input_boolean.maestro_unit_test"

        # Ensure test entity exists in Home Assistant
        state_manager.hass_client.set_entity(
            entity_id=test_entity_id,
            state="off",
            attributes={"friendly_name": "Test Cache Entity"},
        )

        # Clean up any existing cached data
        redis_key_prefix = f"{STATE_CACHE_PREFIX}:{test_entity_id.replace('.', ':')}"
        cached_keys = state_manager.redis_client.get_keys(f"{redis_key_prefix}*")
        if cached_keys:
            state_manager.redis_client.delete(*cached_keys)

        # Create a dummy state change event
        now = utc_now()
        new_attributes = {"friendly_name": "Test Cache Entity", "changed": True}
        # Add custom attributes like the route does
        new_attributes["last_changed"] = now
        new_attributes["last_updated"] = now
        new_attributes["previous_state"] = "off"
        
        state_change_event = StateChangeEvent(
            timestamp=now,
            time_fired=now,
            event_type="state_changed",
            entity_id=test_entity_id,
            old_state="off",
            new_state="on",
            old_attributes={"friendly_name": "Test Cache Entity"},
            new_attributes=new_attributes,
        )

        # Cache the state change
        state_manager.cache_state_change(state_change_event)

        # Verify the new state was cached
        cached_state = state_manager.get_cached_state(test_entity_id)
        assert cached_state == "on"

        # Verify custom attributes were cached
        cached_last_changed = state_manager.get_cached_state(f"{test_entity_id}.last_changed")
        assert cached_last_changed == now

        cached_last_updated = state_manager.get_cached_state(f"{test_entity_id}.last_updated")
        assert cached_last_updated == now

        cached_previous_state = state_manager.get_cached_state(f"{test_entity_id}.previous_state")
        assert cached_previous_state == "off"

        # Verify new attributes were cached
        cached_friendly_name = state_manager.get_cached_state(f"{test_entity_id}.friendly_name")
        assert cached_friendly_name == "Test Cache Entity"

        cached_changed = state_manager.get_cached_state(f"{test_entity_id}.changed")
        assert cached_changed is True

    def test_cache_state_change_entity_deletion(self, state_manager: StateManager) -> None:
        """Test caching a state change event when entity is deleted (new_state is None)"""
        test_entity_id = "maestro.unit_test"

        # Set up initial cached state and attributes
        state_manager.set_cached_state(test_entity_id, "on")
        state_manager.set_cached_state(f"{test_entity_id}.friendly_name", "Test Entity")
        state_manager.set_cached_state(f"{test_entity_id}.some_attribute", "some_value")

        # Verify initial state is cached
        assert state_manager.get_cached_state(test_entity_id) == "on"
        assert state_manager.get_cached_state(f"{test_entity_id}.friendly_name") == "Test Entity"
        assert state_manager.get_cached_state(f"{test_entity_id}.some_attribute") == "some_value"

        # Create a state change event representing entity deletion
        now = utc_now()
        deletion_event = StateChangeEvent(
            timestamp=now,
            time_fired=now,
            event_type="state_changed",
            entity_id=test_entity_id,
            old_state="on",
            new_state=None,  # Entity deletion
            old_attributes={"friendly_name": "Test Entity", "some_attribute": "some_value"},
            new_attributes={},
        )

        # Cache the deletion event
        state_manager.cache_state_change(deletion_event)

        # Verify all cached data for this entity was deleted
        assert state_manager.get_cached_state(test_entity_id) is None
        assert state_manager.get_cached_state(f"{test_entity_id}.friendly_name") is None
        assert state_manager.get_cached_state(f"{test_entity_id}.some_attribute") is None

    def test_cache_state_change_attribute_removal(self, state_manager: StateManager) -> None:
        """Test caching state change event when some attributes are removed"""
        test_entity_id = "maestro.unit_test"

        # Set up initial cached state and attributes
        state_manager.set_cached_state(test_entity_id, "off")
        state_manager.set_cached_state(f"{test_entity_id}.friendly_name", "Test Entity")
        state_manager.set_cached_state(f"{test_entity_id}.old_attribute", "old_value")
        state_manager.set_cached_state(f"{test_entity_id}.persistent_attribute", "persistent_value")

        # Verify initial state
        assert state_manager.get_cached_state(test_entity_id) == "off"
        assert state_manager.get_cached_state(f"{test_entity_id}.old_attribute") == "old_value"
        assert state_manager.get_cached_state(
            f"{test_entity_id}.persistent_attribute"
        ) == "persistent_value"

        # Create state change event where old_attribute is removed but persistent_attribute remains
        now = utc_now()
        state_change_event = StateChangeEvent(
            timestamp=now,
            time_fired=now,
            event_type="state_changed",
            entity_id=test_entity_id,
            old_state="off",
            new_state="on",
            old_attributes={
                "friendly_name": "Test Entity",
                "old_attribute": "old_value",
                "persistent_attribute": "persistent_value"
            },
            new_attributes={
                "friendly_name": "Test Entity",
                "persistent_attribute": "updated_value",
                "new_attribute": "new_value"
            },
        )

        # Cache the state change
        state_manager.cache_state_change(state_change_event)

        # Verify state was updated
        assert state_manager.get_cached_state(test_entity_id) == "on"

        # Verify old_attribute was removed from cache
        assert state_manager.get_cached_state(f"{test_entity_id}.old_attribute") is None

        # Verify persistent_attribute was updated
        assert state_manager.get_cached_state(
            f"{test_entity_id}.persistent_attribute"
        ) == "updated_value"

        # Verify new_attribute was added
        assert state_manager.get_cached_state(f"{test_entity_id}.new_attribute") == "new_value"

        # Verify friendly_name persists
        assert state_manager.get_cached_state(f"{test_entity_id}.friendly_name") == "Test Entity"


class TestStateManagerUnit:
    def test_encode_cached_state_string(self) -> None:
        """Test encoding string values"""
        result = StateManager.encode_cached_state("test_string")
        data = json.loads(result)

        assert data["value"] == "test_string"
        assert data["type"] == "str"

    def test_encode_cached_state_int(self) -> None:
        """Test encoding integer values"""
        result = StateManager.encode_cached_state(42)
        data = json.loads(result)

        assert data["value"] == "42"
        assert data["type"] == "int"

    def test_encode_cached_state_float(self) -> None:
        """Test encoding float values"""
        result = StateManager.encode_cached_state(3.14)
        data = json.loads(result)

        assert data["value"] == "3.14"
        assert data["type"] == "float"

    def test_encode_cached_state_dict(self) -> None:
        """Test encoding dictionary values"""
        test_dict = {"key": "value", "nested": {"inner": "data"}}
        result = StateManager.encode_cached_state(test_dict)
        data = json.loads(result)

        assert data["value"] == json.dumps(test_dict)
        assert data["type"] == "dict"

    def test_encode_cached_state_datetime(self) -> None:
        """Test encoding datetime values"""
        test_datetime = utc_now().replace(microsecond=0)  # Remove microseconds for clean comparison
        result = StateManager.encode_cached_state(test_datetime)
        data = json.loads(result)

        assert data["value"] == test_datetime.isoformat()
        assert data["type"] == "datetime"

    def test_encode_cached_state_none(self) -> None:
        """Test encoding None values"""
        result = StateManager.encode_cached_state(None)
        data = json.loads(result)

        assert data["value"] == ""
        assert data["type"] == "NoneType"

    def test_encode_cached_state_unsupported_type(self) -> None:
        """Test encoding unsupported type raises TypeError"""
        with pytest.raises(TypeError, match="No state encoder exists for type"):
            StateManager.encode_cached_state(object())  # type: ignore[arg-type]

    def test_decode_cached_state_string(self) -> None:
        """Test decoding string values"""
        cached_state = CachedState(value="test_string", type="str")
        result = StateManager.decode_cached_state(cached_state)

        assert result == "test_string"
        assert isinstance(result, str)

    def test_decode_cached_state_int(self) -> None:
        """Test decoding integer values"""
        cached_state = CachedState(value="42", type="int")
        result = StateManager.decode_cached_state(cached_state)

        assert result == 42
        assert isinstance(result, int)

    def test_decode_cached_state_float(self) -> None:
        """Test decoding float values"""
        cached_state = CachedState(value="3.14", type="float")
        result = StateManager.decode_cached_state(cached_state)

        assert result == 3.14
        assert isinstance(result, float)

    def test_decode_cached_state_dict(self) -> None:
        """Test decoding dictionary values"""
        test_dict = {"key": "value", "nested": {"inner": "data"}}
        cached_state = CachedState(value=json.dumps(test_dict), type="dict")
        result = StateManager.decode_cached_state(cached_state)

        assert result == test_dict
        assert isinstance(result, dict)

    def test_decode_cached_state_datetime(self) -> None:
        """Test decoding datetime values"""
        test_datetime = utc_now().replace(microsecond=0)  # Remove microseconds for clean comparison
        cached_state = CachedState(value=test_datetime.isoformat(), type="datetime")
        result = StateManager.decode_cached_state(cached_state)

        assert result == test_datetime
        assert isinstance(result, datetime)

    def test_decode_cached_state_none(self) -> None:
        """Test decoding None values"""
        cached_state = CachedState(value="", type="NoneType")
        result = StateManager.decode_cached_state(cached_state)

        assert result is None

    def test_decode_cached_state_unsupported_type(self) -> None:
        """Test decoding unsupported type raises TypeError"""
        cached_state = CachedState(value="test", type="unsupported_type")
        with pytest.raises(TypeError, match="No state decoder exists for type"):
            StateManager.decode_cached_state(cached_state)

    def test_roundtrip_encoding_string(self) -> None:
        """Test roundtrip encoding/decoding preserves string values"""
        original = "test_string"
        encoded = StateManager.encode_cached_state(original)
        data = json.loads(encoded)
        cached_state = CachedState(value=data["value"], type=data["type"])
        decoded = StateManager.decode_cached_state(cached_state)

        assert decoded == original
        assert type(decoded) is type(original)

    def test_roundtrip_encoding_complex_dict(self) -> None:
        """Test roundtrip encoding/decoding preserves complex dictionary"""
        original = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "nested": {"inner": {"deep": "data"}},
            "list": [1, 2, 3, "mixed", {"nested": "in_list"}],
        }
        encoded = StateManager.encode_cached_state(original)
        data = json.loads(encoded)
        cached_state = CachedState(value=data["value"], type=data["type"])
        decoded = StateManager.decode_cached_state(cached_state)

        assert decoded == original
        assert type(decoded) is type(original)

    @patch.object(RedisClient, "get")
    @patch.object(RedisClient, "build_key")
    def test_get_cached_state_valid_data(self, mock_build_key: Mock, mock_get: Mock) -> None:
        """Test get_cached_state with valid cached data"""
        mock_build_key.return_value = f"{STATE_CACHE_PREFIX}:entity:attr"
        mock_get.return_value = '{"value": "42", "type": "int"}'

        state_manager = StateManager()
        result = state_manager.get_cached_state("entity.attr")

        assert result == 42
        assert isinstance(result, int)
        mock_build_key.assert_called_once_with(STATE_CACHE_PREFIX, "entity", "attr")
        mock_get.assert_called_once_with(key=f"{STATE_CACHE_PREFIX}:entity:attr")

    @patch.object(RedisClient, "get")
    @patch.object(RedisClient, "build_key")
    def test_get_cached_state_no_data(self, mock_build_key: Mock, mock_get: Mock) -> None:
        """Test get_cached_state when no cached data exists"""
        mock_build_key.return_value = f"{STATE_CACHE_PREFIX}:entity:attr"
        mock_get.return_value = None

        state_manager = StateManager()
        result = state_manager.get_cached_state("entity.attr")

        assert result is None

    @patch.object(RedisClient, "set")
    @patch.object(RedisClient, "build_key")
    def test_set_cached_state_new_value(self, mock_build_key: Mock, mock_set: Mock) -> None:
        """Test set_cached_state with new value (no previous value)"""
        mock_build_key.return_value = f"{STATE_CACHE_PREFIX}:entity:attr"
        mock_set.return_value = None  # No previous value

        state_manager = StateManager()
        result = state_manager.set_cached_state("entity.attr", "new_value")

        assert result is None
        mock_build_key.assert_called_once_with(STATE_CACHE_PREFIX, "entity", "attr")
        # Verify the encoded JSON was passed to Redis
        mock_set.assert_called_once()
        encoded_json = mock_set.call_args[0][1]
        data = json.loads(encoded_json)
        assert data["value"] == "new_value"
        assert data["type"] == "str"

    @patch.object(RedisClient, "set")
    @patch.object(RedisClient, "build_key")
    def test_set_cached_state_with_previous_value(
        self, mock_build_key: Mock, mock_set: Mock
    ) -> None:
        """Test set_cached_state returns previous value when it exists"""
        mock_build_key.return_value = f"{STATE_CACHE_PREFIX}:entity:attr"
        mock_set.return_value = '{"value": "old_value", "type": "str"}'

        state_manager = StateManager()
        result = state_manager.set_cached_state("entity.attr", "new_value")

        assert result == "old_value"

    def test_set_cached_state_invalid_key_format(self) -> None:
        """Test set_cached_state with invalid key format"""
        state_manager = StateManager()

        with pytest.raises(ValueError, match="Invalid format"):
            state_manager.set_cached_state("invalid_key", "value")

        with pytest.raises(ValueError, match="Invalid format"):
            state_manager.set_cached_state("too.many.parts.here", "value")

    def test_set_cached_state_non_string_state_value(self) -> None:
        """Test set_cached_state with non-string state value (2 parts = entity state)"""
        state_manager = StateManager()

        with pytest.raises(TypeError, match="State value must be a string"):
            state_manager.set_cached_state("entity.state", 42)  # 2 parts, so it's a state

    def test_set_cached_state_allows_non_string_attribute(self) -> None:
        """Test set_cached_state allows non-string for attribute values (3 parts)"""
        state_manager = StateManager()

        with (
            patch.object(RedisClient, "set", return_value=None),
            patch.object(RedisClient, "build_key", return_value="key"),
        ):
            # This should not raise an error - 3 parts means it's an attribute
            result = state_manager.set_cached_state("entity.state.attr", 42)
            assert result is None

    def test_get_cached_state_invalid_key_format(self) -> None:
        """Test get_cached_state with invalid key format"""
        state_manager = StateManager()

        with pytest.raises(ValueError, match="Invalid format"):
            state_manager.get_cached_state("invalid_key")

        with pytest.raises(ValueError, match="Invalid format"):
            state_manager.get_cached_state("too.many.parts.here.now")

    @patch.object(RedisClient, "get_keys")
    def test_get_all_entity_keys(self, mock_get_keys: Mock) -> None:
        """Test get_all_entity_keys returns all cached keys for an entity"""
        mock_get_keys.return_value = [
            f"{STATE_CACHE_PREFIX}:sensor:temperature:friendly_name",
            f"{STATE_CACHE_PREFIX}:sensor:temperature:unit_of_measurement",
            f"{STATE_CACHE_PREFIX}:sensor:temperature:device_class",
        ]

        state_manager = StateManager()
        result = state_manager.get_all_entity_keys("sensor.temperature")

        expected_keys = [
            f"{STATE_CACHE_PREFIX}:sensor:temperature",
            f"{STATE_CACHE_PREFIX}:sensor:temperature:friendly_name",
            f"{STATE_CACHE_PREFIX}:sensor:temperature:unit_of_measurement",
            f"{STATE_CACHE_PREFIX}:sensor:temperature:device_class",
        ]

        assert result == expected_keys
        mock_get_keys.assert_called_once_with(pattern=f"{STATE_CACHE_PREFIX}:sensor:temperature:*")

    def test_state_key_classmethod(self) -> None:
        """Test state_key class method builds correct Redis keys"""
        # Test entity state key (2 parts)
        entity_key = StateManager.state_key("sensor.temperature")
        assert entity_key == f"{STATE_CACHE_PREFIX}:sensor:temperature"

        # Test attribute key (3 parts)
        attr_key = StateManager.state_key("sensor.temperature.friendly_name")
        assert attr_key == f"{STATE_CACHE_PREFIX}:sensor:temperature:friendly_name"

    def test_state_key_invalid_format(self) -> None:
        """Test state_key raises ValueError for invalid formats"""
        with pytest.raises(ValueError, match="Invalid format"):
            StateManager.state_key("invalid_key")

        with pytest.raises(ValueError, match="Invalid format"):
            StateManager.state_key("too.many.parts.here.now")
