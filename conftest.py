"""
Pytest configuration for Maestro tests.

This file makes the maestro_test fixture and other testing utilities
available to all test files without needing explicit imports.
"""

# Import fixtures to make them available to all tests
pytest_plugins = ["maestro.utils.testing.fixtures"]
