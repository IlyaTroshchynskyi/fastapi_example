---
name: fastapi-service
description: Defines the layered structure and conventions of a FastAPI feature module in this codebase. Use when creating or modifying a FastAPI feature module — services, routers, schemas, use cases, or enums — in this codebase. Apply to all new feature work.
---

# FastAPI Feature Service Pattern

## Feature Module File Layout

```
app/apps/<domain>/
  __init__.py
  routes.py          # thin HTTP controllers
  schemas.py         # Pydantic request/response models
  models.py          # SQLAlchemy ORM model (extends MixinsBase)
  repository.py      # data access only (see create-repository skill)
  services/
    __init__.py
    service.py       # business logic
  use_cases/         # only when a route needs multiple services
    __init__.py
    <verb>_<noun>.py
```

Add `use_cases/` only when a route orchestrates multiple services (e.g. create user + send email + publish MQ). For simple CRUD, call the service directly from the route.

---

## New Feature Checklist

Copy this checklist and tick items off as you go:

- [ ] `models.py` — model extends `MixinsBase`
- [ ] `make migration MSG='...'` — never write migrations by hand; confirm the generated revision contains exactly the expected changes, then `make migrate`
- [ ] `schemas.py` — request and response schemas
- [ ] `repository.py` — see `create-repository` skill
- [ ] `services/service.py` — business logic, domain exceptions only
- [ ] `use_cases/` — only if a route coordinates multiple services
- [ ] `routes.py` — thin controllers; router registered in `app/main.py`
- [ ] Tests in `tests/api/test_<domain>.py` — see `testing-rules-styles` skill
- [ ] `make lint` → `make lint-no-format` → `make test` (needs `docker compose up -d`); fix and re-run until all three pass

---

## Service Layer

Inject dependencies via FastAPI's `Depends()` in `__init__`. Store as attributes (private for external collaborators, public for the repository).

```python
from typing import Annotated
from fastapi import Depends
from app.apps.<domain>.repository import <Domain>Repository
from app.apps.<domain>.schemas import <Domain>Schema, <Domain>CreateSchema
from app.core.exceptions import AlreadyExistError


class <Domain>Service:
    def __init__(
        self,
        <domain>_repository: Annotated[<Domain>Repository, Depends(<Domain>Repository)],
    ) -> None:
        self.<domain>_repository = <domain>_repository

    async def list_<domains>(self) -> list[<Domain>Schema]:
        return await self.<domain>_repository.list_all()

    async def get_<domain>_by_id(self, _id: int) -> <Domain>Schema:
        return await self.<domain>_repository.get_by_id(_id)

    async def create_<domain>(self, <domain>_creation: <Domain>CreateSchema) -> <Domain>Schema:
        return await self.<domain>_repository.create(<domain>_creation)
```

Rules:
- Method names follow `.claude/rules/naming.md`: `list_<domains>`, `get_<domain>_by_id` (raises `NotFoundError`), `find_<domain>_by_<field>` (may return `None`), `create_<domain>`, `update_<domain>`, `delete_<domain>`
- Always `async`
- Raise domain exceptions only (`NotFoundError`, `AlreadyExistError` from `app.core.exceptions`) — **never `HTTPException`**, never `from fastapi import ...`
- Return typed Pydantic schemas
- Protected helpers at the bottom of the class

---

## Use Case Layer

For workflows that span multiple services or external calls:

```python
from fastapi import Depends
from faststream.rabbit import RabbitBroker
from app.apps.<domain>.schemas import <Domain>CreateSchema, <Domain>Schema
from app.apps.<domain>.services.service import <Domain>Service
from app.core.config import get_settings, Settings
from app.core.exceptions import AlreadyExistError
from app.core.services.ses import SesEmailSenderService


class Register<Domain>UseCase:
    def __init__(
        self,
        <domain>_service: <Domain>Service = Depends(),
        notification_service: SesEmailSenderService = Depends(),
        settings: Settings = Depends(get_settings),
    ) -> None:
        self._<domain>_service = <domain>_service
        self._notification_service = notification_service
        self._settings = settings

    async def execute(self, <domain>_creation: <Domain>CreateSchema, broker: RabbitBroker) -> <Domain>Schema:
        existing_<domain> = await self._<domain>_service.find_<domain>_by_email(<domain>_creation.email)
        if existing_<domain>:
            raise AlreadyExistError('Already registered')
        new_<domain> = await self._<domain>_service.create_<domain>(<domain>_creation)
        await self._notification_service.send_email(...)
        await self._publish_<domain>_creation_message(broker, <domain>_creation)
        return new_<domain>

    async def _publish_<domain>_creation_message(
        self, broker: RabbitBroker, <domain>_creation: <Domain>CreateSchema
    ) -> None:
        ...
```

---

## Router Rules — Thin Controllers Only

- **No business logic** — delegate to service or use case
- **No database access**
- **No `if` statements in the happy path** — any branching belongs in the service
- Catch domain exceptions and convert to `HTTPException`
- `GET` → 200 (default)
- `POST` → `status_code=201`
- `DELETE` → `status_code=204, response_class=Response`

```python
from fastapi import APIRouter, Depends, HTTPException, Response
from app.apps.<domain>.schemas import <Domain>CreateSchema, <Domain>Schema, <Domain>UpdateSchema
from app.apps.<domain>.services.service import <Domain>Service
from app.core.exceptions import AlreadyExistError, NotFoundError

router = APIRouter(tags=['<Domain>'])


@router.get('/<domains>')
async def list_<domains>(service: <Domain>Service = Depends()) -> list[<Domain>Schema]:
    return await service.list_<domains>()


@router.get('/<domains>/{<domain>_id}')
async def get_<domain>_by_id(<domain>_id: int, service: <Domain>Service = Depends()) -> <Domain>Schema:
    try:
        return await service.get_<domain>_by_id(<domain>_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post('/<domains>', status_code=201)
async def create_<domain>(
    <domain>_creation: <Domain>CreateSchema, service: <Domain>Service = Depends()
) -> <Domain>Schema:
    return await service.create_<domain>(<domain>_creation)


@router.put('/<domains>/{<domain>_id}')
async def update_<domain>(
    <domain>_id: int, <domain>_update: <Domain>UpdateSchema, service: <Domain>Service = Depends()
) -> <Domain>Schema:
    try:
        return await service.update_<domain>(<domain>_update, <domain>_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except AlreadyExistError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.delete('/<domains>/{<domain>_id}', status_code=204, response_class=Response)
async def delete_<domain>(<domain>_id: int, service: <Domain>Service = Depends()) -> None:
    try:
        await service.delete_<domain>(<domain>_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
```

Register the router in `app/main.py` via `_app.include_router(...)`.

---

## Schema Conventions

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class <Domain>CreateSchema(BaseModel):
    name: str = Field(max_length=64)  # max_length must be a multiple of 2


class <Domain>UpdateSchema(<Domain>CreateSchema):
    pass


class <Domain>Schema(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

- `model_config = ConfigDict(from_attributes=True)` on response schemas
- Optional fields: `field: str | None = Field(default=None)`. Required constrained fields: `field: str = Field(max_length=64)`. Never use `...` as a positional default
- String column lengths must be a multiple of 2

---

## Model Convention

All models extend `MixinsBase` (provides `id`, `created_at`, `updated_at`):

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import MixinsBase


class <Domain>Model(MixinsBase):
    __tablename__ = '<domains>'

    name: Mapped[str] = mapped_column(String(64))
```

---

## Enum Convention

All enums in `app/core/enums.py` (project-wide) or the domain's `enums.py` if domain-specific. Use `StrEnum`:

```python
from enum import StrEnum

class GenreStatus(StrEnum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
```

---

## Exception Decision Tree

```
Does app.core.exceptions already express this error?
  YES → raise it from the service; router catches and maps to HTTPException
    NotFoundError     → 404
    AlreadyExistError → 409

  NO → raise a specific exception from the service; router MUST catch it manually
```

---

## Anti-Patterns

| Pattern | Why It Fails |
|---|---|
| `raise HTTPException(...)` in service | Couples business logic to HTTP — untestable without HTTP layer |
| Business logic in router (`if`/`else`) | Violates thin-controller rule |
| Direct DB access in router | Repository is the only DB layer |
| Enums inline in `schemas.py` or `models.py` | Hard to import without pulling the whole module |
| `from fastapi import ...` in service | Makes service framework-dependent |
| `DELETE` without `response_class=Response` | FastAPI tries to serialize `None` and may 500 |
| `POST` returning 200 | Use 201 to signal resource creation |

## Common Mistakes

- **Forgetting `response_class=Response` on DELETE**: Without it FastAPI tries to serialize `None` and may 500.
- **Using `Exception` base for cross-cutting errors**: Prefer `core/exceptions.py` — routers already map those exceptions to `HTTPException` (there is no global exception handler in `app/main.py`).