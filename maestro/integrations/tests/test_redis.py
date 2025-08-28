import time

import pytest

from maestro.integrations.redis import RedisClient


class TestRedisClient:
    @pytest.fixture(scope="class")
    def client(self) -> RedisClient:
        return RedisClient()

    @pytest.fixture(scope="class", autouse=True)
    def check_health_or_skip(self, client: RedisClient) -> None:
        """Check Redis health before running other tests. Skip all if unhealthy."""
        if not client.check_health():
            pytest.skip("Redis is not healthy - skipping all integration tests")

    def test_check_health(self, client: RedisClient) -> None:
        """Test that Redis is accessible and returns expected health response."""
        is_healthy = client.check_health()
        assert is_healthy is True

    def test_set_and_get(self, client: RedisClient) -> None:
        """Test setting and getting string values."""
        test_key = "maestro:test:string"
        test_value = "test_value"

        # Clean up first
        client.delete(test_key)

        # Set value
        old_value = client.set(test_key, test_value)
        assert old_value is None  # No previous value

        # Get value
        retrieved_value = client.get(test_key)
        assert retrieved_value == test_value

        # Update value and check old value is returned
        new_value = "updated_value"
        old_value = client.set(test_key, new_value)
        assert old_value == test_value

        # Verify new value
        retrieved_value = client.get(test_key)
        assert retrieved_value == new_value

        client.delete(test_key)

    def test_set_with_ttl(self, client: RedisClient) -> None:
        """Test setting values with TTL."""
        test_key = "maestro:test:ttl"
        test_value = "expires_soon"

        # Clean up first
        client.delete(test_key)

        # Set with short TTL (1 second)
        client.set(test_key, test_value, ttl_seconds=1)

        # Should exist immediately
        assert client.exists(test_key) == 1
        retrieved_value = client.get(test_key)
        assert retrieved_value == test_value

        # Should no longer exist
        time.sleep(1.1)
        assert client.exists(test_key) == 0
        assert client.get(test_key) is None

    def test_delete_and_exists(self, client: RedisClient) -> None:
        """Test deleting keys and checking existence."""
        test_key1 = "maestro:test:delete1"
        test_key2 = "maestro:test:delete2"
        test_value = "to_be_deleted"

        # Set up test data
        client.set(test_key1, test_value)
        client.set(test_key2, test_value)

        # Verify they exist
        assert client.exists(test_key1) == 1
        assert client.exists(test_key2) == 1
        assert client.exists(test_key1, test_key2) == 2

        # Delete one key
        deleted_count = client.delete(test_key1)
        assert deleted_count == 1

        # Verify deletion
        assert client.exists(test_key1) == 0
        assert client.exists(test_key2) == 1
        assert client.get(test_key1) is None
        assert client.get(test_key2) == test_value

        # Delete multiple keys
        deleted_count = client.delete(test_key2, "nonexistent_key")
        assert deleted_count == 1  # Only test_key2 existed

    def test_get_keys(self, client: RedisClient) -> None:
        """Test getting all keys."""
        # Set up test keys with a unique prefix
        test_prefix = "maestro:test:keys"
        test_keys = [f"{test_prefix}:1", f"{test_prefix}:2", f"{test_prefix}:3"]

        # Clean up any existing test keys
        client.delete(*test_keys)

        # Set test data
        for key in test_keys:
            client.set(key, "test_value")

        # Get all keys
        all_keys = client.get_keys()

        # Verify our test keys are in the result
        for test_key in test_keys:
            assert test_key in all_keys

        # Clean up
        client.delete(*test_keys)

    def test_nonexistent_key(self, client: RedisClient) -> None:
        """Test operations on nonexistent keys."""
        nonexistent_key = "maestro:test:nonexistent"

        # Ensure key doesn't exist
        client.delete(nonexistent_key)

        # Get should return None
        assert client.get(nonexistent_key) is None

        # Exists should return 0
        assert client.exists(nonexistent_key) == 0

        # Delete should return 0
        assert client.delete(nonexistent_key) == 0

    def test_empty_string_value(self, client: RedisClient) -> None:
        """Test handling empty string values."""
        test_key = "maestro:test:empty"

        # Clean up first
        client.delete(test_key)

        # Set empty string
        client.set(test_key, "")

        # Should exist and return empty string
        assert client.exists(test_key) == 1
        assert client.get(test_key) == ""

        # Clean up
        client.delete(test_key)

    def test_key_patterns(self, client: RedisClient) -> None:
        """Test various key naming patterns."""
        test_keys = [
            "maestro:test:simple",
            "maestro:test:with-dashes",
            "maestro:test:with_underscores",
            "maestro:test:with.dots",
            "maestro:test:with:colons",
        ]

        # Clean up first
        client.delete(*test_keys)

        # Set values for all key patterns
        for i, key in enumerate(test_keys):
            client.set(key, f"value_{i}")

        # Verify all keys can be retrieved
        for i, key in enumerate(test_keys):
            assert client.get(key) == f"value_{i}"
            assert client.exists(key) == 1

        # Clean up
        client.delete(*test_keys)
