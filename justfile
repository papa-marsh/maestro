# Build the Docker image
build:
    docker compose build maestro

# Rebuild and redeploy the app
deploy:
    docker compose down
    just kill-shell
    docker compose up -d --build
    sleep 1
    just logs

# Deploy after pulling from the remote
pull-deploy:
    git checkout main && git pull
    just deploy

# Deploy after "force pulling" from the remote
pull-deploy-f:
    git checkout main && git fetch origin && git reset --hard origin/main
    just deploy

# Update the pinned hass-maestro library version
upgrade-maestro:
    uv lock --upgrade-package hass-maestro

# Kill any dangling "flask shell" docker containers
kill-shell:
    docker ps --no-trunc --format '{{ "{{" }}.ID{{ "}}" }} {{ "{{" }}.Command{{ "}}" }}' | grep "flask shell" | awk '{print $1}' | xargs -r docker rm -f

# Get logs from the maestro container
logs:
    docker compose logs maestro | grep -v 'debug'

# Open a Flask shell in the container with pre-loaded imports (no background services)
shell: build
    docker compose run --rm -e FLASK_APP=app:app -e MAESTRO_BACKGROUND_SERVICES=false maestro uv run --no-dev flask shell

# Open an interactive bash shell in the container
bash: build
    docker compose run --rm maestro bash

# Prune registry entities that no longer exist in Home Assistant
prune: build
    docker compose run --rm -e MAESTRO_BACKGROUND_SERVICES=false maestro uv run --no-dev python -c "import app; from maestro.registry import RegistryManager; RegistryManager.prune()"
