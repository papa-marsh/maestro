.PHONY: build test test-integration test-home-assistant test-specific test-specific-verbose shell bash

# Build the Docker image
build:
	docker compose build maestro

# Rebuild and redeploy the app
deploy:
	docker compose down && docker compose up -d --build

# Deploy after pulling the maestro & scripts repos from their remotes
pull-deploy:
	git pull && cd scripts && git pull && cd .. && docker compose down && docker compose up -d --build && sleep 2 && make logs

# Get logs from the maestro container
logs:
	docker compose logs maestro

# Run all tests or include a path like `TEST=maestro/integrations/tests/test_home_assistant.py::TestHomeAssistantProvider`
test: build
	docker compose run --rm maestro pytest -v $(TEST)

# Open a Flask shell in the container with pre-loaded imports
shell: build
	docker compose run --rm -e FLASK_APP=maestro.app:app maestro flask shell

# Open an interactive bash shell in the container
bash: build
	docker compose run --rm maestro bash
