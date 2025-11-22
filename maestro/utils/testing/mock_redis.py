"""Mock Redis client for testing that stores data in memory."""

from typing import Any


class MockRedisClient:
    """In-memory mock of RedisClient for testing without a Redis instance."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def check_health(self) -> bool:
        """Always returns True for mock client."""
        return True

    def get(self, key: str) -> str | None:
        """Get a value by key from in-memory store."""
        return self._store.get(key)

    def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> str | None:
        """Set a value in the in-memory store. Returns old value if existed."""
        old_value = self._store.get(key)
        self._store[key] = value
        return old_value

    def delete(self, *keys: str) -> int:
        """Delete one or more keys. Returns number of keys deleted."""
        deleted_count = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                deleted_count += 1
        return deleted_count

    def exists(self, *keys: str) -> int:
        """Check if keys exist. Returns count of existing keys."""
        return sum(1 for key in keys if key in self._store)

    def get_keys(self, pattern: str | None = None) -> list[str]:
        """Returns a list of keys, optionally filtered by pattern."""
        if pattern is None:
            return list(self._store.keys())

        # Simple pattern matching: convert Redis pattern to basic matching
        # Supports * (any chars) and basic patterns
        import re

        regex_pattern = pattern.replace("*", ".*")
        regex = re.compile(f"^{regex_pattern}$")
        return [key for key in self._store.keys() if regex.match(key)]

    @classmethod
    def build_key(cls, *parts: str) -> str:
        """Builds a redis key from provided args."""
        return ":".join(parts)

    def clear(self) -> None:
        """Clear all stored data. Useful for test cleanup."""
        self._store.clear()

    def get_all(self) -> dict[str, str]:
        """Get all stored data. Useful for debugging tests."""
        return self._store.copy()
