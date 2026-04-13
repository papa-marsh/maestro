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

# Pull both repos
pull:
    git checkout main && git pull
    cd scripts && git checkout main && git pull

# Deploy after pulling the maestro & scripts repos from their remotes
pull-deploy:
    git checkout main && git pull
    cd scripts && git checkout main && git pull
    docker compose down
    just kill-shell
    docker compose up -d --build
    sleep 1
    just logs

# Deploy after "force pulling" the maestro & scripts repos from their remotes
pull-deploy-f:
    git checkout main && git fetch origin && git reset --hard origin/main
    cd scripts && git checkout main && git fetch origin && git reset --hard origin/main
    docker compose down
    just kill-shell
    docker compose up -d --build
    sleep 1
    just logs

# Kill any running "flask shell" docker containers
kill-shell:
    docker ps --format '{{ "{{" }}.ID{{ "}}" }} {{ "{{" }}.Command{{ "}}" }}' | grep "flask shell" | awk '{print $1}' | xargs -r docker rm -f

# Get logs from the maestro container
logs:
    docker compose logs maestro | grep -v 'debug'

# Open a Flask shell in the container with pre-loaded imports
shell: build
    docker compose run --rm -e FLASK_APP=maestro.app:app maestro uv run --no-dev flask shell

# Open an interactive bash shell in the container
bash: build
    docker compose run --rm maestro bash
