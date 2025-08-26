.PHONY: build test test-integration test-home-assistant test-specific test-specific-verbose

# Build the Docker image
build:
	docker compose build maestro

# Run all tests or include a path like `TEST=maestro/integrations/tests/test_home_assistant.py::TestHomeAssistantProvider`
test: build
	docker compose run --rm maestro pytest -v $(TEST)
