# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync --all-groups          # install all dependencies
docker compose up -d          # start Postgres (5436), test Postgres (5437), RabbitMQ (5672)

make run_app                  # uvicorn on port 8005 with reload
make migrate                  # alembic upgrade head
make migration MSG='...'      # autogenerate an Alembic revision (never write migrations by hand)

make lint                     # ruff format + ruff check --fix
make lint-no-format           # ruff check (no write) + mypy
make typecheck                # mypy only

make test                     # pytest with coverage (requires docker compose up -d)
pytest tests/api/test_users.py::TestUsersAPI::test_create_user   # run a single test

uv run pre-commit install     # install hooks once per clone
```

Tests expect Postgres on `localhost:5437`, RabbitMQ on `localhost:5672`, and spin up a MinIO Testcontainer for S3.

## Architecture

### Module layout

Each feature lives under `app/apps/<domain>/` and follows a strict layered structure:

```
routes.py        → FastAPI router; converts HTTP ↔ service/use-case calls; raises HTTPException
schemas.py       → Pydantic v2 request/response models
models.py        → SQLAlchemy ORM model (inherits MixinsBase)
repository.py    → DB access (inherits BaseRepositoryImpl or its Protocol)
services/        → Business logic; orchestrates repository calls
use_cases/       → Complex cross-service workflows (e.g. RegisterUserUseCase)
```

Use cases are used when a route needs to coordinate multiple services (e.g. create user + send email + publish MQ message). For simpler routes, service is called directly from the route.

### Shared infrastructure (`app/core/`)

| File/Package | Purpose |
|---|---|
| `database.py` | `MixinsBase` (id, created_at, updated_at), async engine/session factory, `get_session` dependency, `get_alembic_config` |
| `repositories/base_repository.py` | `BaseRepositoryImpl` generic CRUD + `BaseRepositoryProtocol` for typing |
| `config.py` | `Settings` (pydantic-settings); use `get_settings()` dependency, never read `.env` directly |
| `exceptions.py` | Domain exceptions (`NotFoundError`, `AlreadyExistError`); routes convert these to HTTPException |
| `infrastructure/brokers/` | RabbitMQ broker via FastStream; use `get_rabbit_broker` dependency |
| `services/s3_storage.py` | aiobotocore S3 client wrappers |
| `services/ses.py` | SES email sender |
| `enums.py` | All project-wide enums (use `StrEnum`) |

### Message consumers

FastStream RabbitMQ consumers live under `app/apps/consumers/` and are registered as FastAPI routers in `main.py`. Exchange and queue definitions are in `exchanges.py` / `queues.py`.

### Testing patterns

- **No DB mocking** — tests hit a real Postgres (localhost:5437); schema is migrated up/down per session via Alembic in `conftest.py`.
- **Transaction rollback per test** — the `session` fixture wraps each test in a transaction that is rolled back, keeping tests isolated.
- **Test base classes** in `conftest.py`: `TestBaseDBClass`, `TestBaseClientClass`, `TestBaseClientDBClass` — inherit the appropriate one.
- **Factories** live in `tests/factory_helpers/`; use `factory_creators`, `factory_getters`, `factory_updaters` helpers.
- **Broker is mocked** via `mock_broker` fixture (`AsyncMock(spec=RabbitBroker)`); S3 uses a real MinIO Testcontainer.
- Assert both status code and response body on error responses.

## Code conventions

- Python 3.12+; no `from __future__ import annotations` unless actually needed.
- `StrEnum` for all enums; keep them in `app/core/enums.py` or the domain's `enums.py`.
- Pydantic v2: `ConfigDict`, `model_config` after fields. Optional fields: `field: str | None = Field(default=None)`. Required constrained fields: `field: str = Field(max_length=64)`. Never use `...` as a positional default. Use `| None` not `Optional`.
- `list[T]` not `List[T]` in type hints.
- `String(n)` column lengths must be a multiple of 2.
- No global values; use FastAPI dependency injection everywhere.
- Protected methods at the end of the class.
- f-strings for all string formatting.
- Always validate payload data and filters; ask if scope is unclear.
- Line length 120; single-quoted strings (enforced by Ruff).