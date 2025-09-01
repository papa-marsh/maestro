import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from maestro.integrations.redis import RedisClient
from maestro.integrations.state_manager import CachedState, StateManager


class TestStateManagerIntegration: ...  # TODO


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
        test_datetime = datetime(2025, 1, 1, 12, 0, 0)
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
        test_datetime = datetime(2025, 1, 1, 12, 0, 0)
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
        mock_build_key.return_value = "STATE:entity:attr"
        mock_get.return_value = '{"value": "42", "type": "int"}'

        state_manager = StateManager()
        result = state_manager.get_cached_state("entity.attr")

        assert result == 42
        assert isinstance(result, int)
        mock_build_key.assert_called_once_with("STATE", "entity", "attr")
        mock_get.assert_called_once_with("STATE:entity:attr")

    @patch.object(RedisClient, "get")
    @patch.object(RedisClient, "build_key")
    def test_get_cached_state_no_data(self, mock_build_key: Mock, mock_get: Mock) -> None:
        """Test get_cached_state when no cached data exists"""
        mock_build_key.return_value = "STATE:entity:attr"
        mock_get.return_value = None

        state_manager = StateManager()
        result = state_manager.get_cached_state("entity.attr")

        assert result is None

    @patch.object(RedisClient, "set")
    @patch.object(RedisClient, "build_key")
    def test_set_cached_state_new_value(self, mock_build_key: Mock, mock_set: Mock) -> None:
        """Test set_cached_state with new value (no previous value)"""
        mock_build_key.return_value = "STATE:entity:attr"
        mock_set.return_value = None  # No previous value

        state_manager = StateManager()
        result = state_manager.set_cached_state("entity.attr", "new_value")

        assert result is None
        mock_build_key.assert_called_once_with("STATE", "entity", "attr")
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
        mock_build_key.return_value = "STATE:entity:attr"
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
