.PHONY: build test test-integration test-home-assistant test-specific test-specific-verbose shell bash

# Build the Docker image
build:
	docker compose build maestro

# Run all tests or include a path like `TEST=maestro/integrations/tests/test_home_assistant.py::TestHomeAssistantProvider`
test: build
	docker compose run --rm maestro pytest -v $(TEST)

# Open a Python shell in the container with app context
shell: build
	docker compose run --rm maestro python

# Open an interactive bash shell in the container
bash: build
	docker compose run --rm maestro bash
