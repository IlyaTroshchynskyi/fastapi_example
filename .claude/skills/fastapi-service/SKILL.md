---
name: fastapi-service
description: Use when creating or modifying a FastAPI feature module — services, routers, schemas, use cases, or enums — in this codebase. Apply to all new feature work.
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

    async def get_all(self) -> list[<Domain>Schema]:
        return await self.<domain>_repository.get_all()

    async def get_by_id(self, _id: int) -> <Domain>Schema:
        return await self.<domain>_repository.get_by_id(_id)

    async def create(self, data: <Domain>CreateSchema) -> <Domain>Schema:
        return await self.<domain>_repository.create(data)
```

Rules:
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
from app.core.exceptions import AlreadyExistError


class Register<Domain>UseCase:
    def __init__(
        self,
        service: <Domain>Service = Depends(),
        notification_service: SesEmailSenderService = Depends(),
        settings: Settings = Depends(get_settings),
    ) -> None:
        self._service = service
        self._notification_service = notification_service
        self._settings = settings

    async def execute(self, data: <Domain>CreateSchema, broker: RabbitBroker) -> <Domain>Schema:
        existing = await self._service.get_by_email(data.email)
        if existing:
            raise AlreadyExistError('Already registered')
        result = await self._service.create(data)
        await self._notification_service.send_email(...)
        await self._publish(broker, data)
        return result

    async def _publish(self, broker: RabbitBroker, data: <Domain>CreateSchema) -> None:
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
from app.apps.<domain>.schemas import <Domain>CreateUpdate, <Domain>Schema
from app.apps.<domain>.services.service import <Domain>Service
from app.core.exceptions import AlreadyExistError, NotFoundError

router = APIRouter(tags=['<Domain>'])


@router.get('/<domains>')
async def list_items(service: <Domain>Service = Depends()) -> list[<Domain>Schema]:
    return await service.get_all()


@router.get('/<domains>/{item_id}')
async def get_item(item_id: int, service: <Domain>Service = Depends()) -> <Domain>Schema:
    try:
        return await service.get_by_id(item_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post('/<domains>', status_code=201)
async def create_item(body: <Domain>CreateUpdate, service: <Domain>Service = Depends()) -> <Domain>Schema:
    return await service.create(body)


@router.put('/<domains>/{item_id}')
async def update_item(
    item_id: int, body: <Domain>CreateUpdate, service: <Domain>Service = Depends()
) -> <Domain>Schema:
    try:
        return await service.update(body, item_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AlreadyExistError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete('/<domains>/{item_id}', status_code=204, response_class=Response)
async def delete_item(item_id: int, service: <Domain>Service = Depends()) -> None:
    try:
        await service.delete(item_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

Register the router in `app/main.py` via `_app.include_router(...)`.

---

## Schema Conventions

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class <Domain>CreateSchema(BaseModel):
    name: str = Field(max_length=64)  # max_length must be a multiple of 2


class <Domain>CreateUpdate(<Domain>CreateSchema):
    pass


class <Domain>Schema(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

- `model_config = ConfigDict(from_attributes=True)` on response schemas
- `Field(default=None)` not `...` for required fields with constraints
- String column lengths must be a multiple of 2

---

## Model Convention

All models extend `MixinsBase` (provides `id`, `created_at`, `updated_at`):

```python
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

class ItemStatus(StrEnum):
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
- **Using `Exception` base for cross-cutting errors**: Prefer `core/exceptions.py` — the global handler already speaks that language.