# fastapi-example

Template FastAPI service with async SQLAlchemy, Alembic, RabbitMQ (FastStream), and S3-style storage hooks.

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/) for dependencies
- Docker (optional, for Postgres, RabbitMQ, and integration-style tests)

## Setup

```bash
uv sync --all-groups
```

Copy environment variables (create `.env` in the repo root). Minimum keys match `app.core.config.Settings`, for example:

| Variable | Purpose |
| --- | --- |
| `ROOT_PATH` | Reverse-proxy path prefix (e.g. `/api`) |
| `ENVIRONMENT` | `local`, `dev`, or `production` |
| `DATABASE_URL` | Async Postgres URL, e.g. `postgresql+psycopg://user:pass@localhost:5436/dbname` |
| `AWS_*`, `S3_*`, `LOCAL_AWS_*` | AWS and S3 / MinIO-related settings |
| `MQ_*` | RabbitMQ URL and exchange/queue names |
| `CORS_ORIGINS` | Optional. Comma-separated browser origins (default: `http://localhost:3000`, `http://127.0.0.1:3000`) |
| `CORS_ALLOW_CREDENTIALS` | Optional. Default `true`; set `false` only if you do not send cookies or `Authorization` from browsers |

Start dependencies:

```bash
docker compose up -d
```

Apply migrations:

```bash
make migrate
```

Run the API:

```bash
make run_app
```

The app listens on port **8005** with reload (see `makefile`). The bundled `Dockerfile` uses port **8006** with `uvicorn` without reload.

## Development

| Command | Description |
| --- | --- |
| `make lint` | Format and lint with Ruff |
| `make lint-no-format` | Ruff check (no write) and Mypy |
| `make test` | Pytest with coverage |
| `make migration MSG='...'` | Autogenerate Alembic revision |

Tests expect Postgres on `localhost:5437`, RabbitMQ on `localhost:5672`, and use Testcontainers for MinIO where needed. Run `docker compose up -d` before `make test` so those services are available.

## Claude Code

The `.claude/` directory is committed to this repository as a reference. It contains:

- `CLAUDE.md` — project guidance loaded automatically by Claude Code
- `skills/` — reusable prompt patterns (repository, service, testing, etc.)
- `agents/` — specialist subagent definitions (tech lead, reviewer, orchestrator, etc.)
- `rules/` — coding rules applied across all agents

Feel free to use, adapt, or extend these for your own projects.

## Pre-commit

Install hooks once per clone:

```bash
uv run pre-commit install
```

Ruff versions are aligned between `pyproject.toml` / `uv.lock` and `.pre-commit-config.yaml`.
