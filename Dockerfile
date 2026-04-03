FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY ./maestro/ ./maestro
COPY ./scripts/ ./scripts

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "gunicorn", "--bind", "0.0.0.0:8000", "maestro.app:app"]
