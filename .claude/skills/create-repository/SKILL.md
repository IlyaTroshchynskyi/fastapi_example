---
name: create-repository
description: Create a SQLAlchemy async repository following the project's canonical pattern. Use when adding a new feature that needs database access or extending an existing repository.
---

# Repository Pattern

## Canonical base class

All repositories extend `BaseRepositoryImpl` from `app.core.repositories.base_repository`.
That class provides `get_by_id`, `get_by_ids`, `get_all`, `create`, `update`, and `delete` out of the box via SQLAlchemy Core with `RETURNING`.

```python
from app.apps.<domain>.models import <Model>
from app.apps.<domain>.schemas import <ModelReadSchema>
from app.core.repositories.base_repository import BaseRepositoryImpl


class <Model>Repository(BaseRepositoryImpl[<Model>, <ModelReadSchema>]):
    db_model = <Model>
    read_schema_type = <ModelReadSchema>
```

That's the complete minimal repository. Only extend it when the feature needs queries beyond the base CRUD.

---

## How the base works

`BaseRepositoryImpl.__init__` injects `AsyncSession` via `Depends(get_session)`. Access it as `self.session`.

Operations use SQLAlchemy Core with `RETURNING` — not the ORM `add / flush / refresh` cycle:

```python
# create (from base — do not repeat this in subclasses)
query = insert(self.db_model).values(**create_object.model_dump()).returning(self.db_model)
model = (await self.session.execute(query)).scalar_one()
return self.read_schema_type.model_validate(model)
```

**Never call `self.session.commit()` in a repository.** The session dependency owns the transaction and commits on request success.

---

## Adding custom query methods

Build queries in a named `query` variable. Chain filters after the base.

```python
from pydantic import TypeAdapter
from sqlalchemy import select
from app.apps.<domain>.schemas import <ModelReadSchema>


class <Model>Repository(BaseRepositoryImpl[<Model>, <ModelReadSchema>]):
    db_model = <Model>
    read_schema_type = <ModelReadSchema>

    async def get_by_name(self, name: str) -> <ModelReadSchema> | None:
        query = select(self.db_model).where(self.db_model.name == name)
        model = (await self.session.execute(query)).scalar_one_or_none()
        if model is None:
            return None
        return self.read_schema_type.model_validate(model)

    async def list_active(self, limit: int = 100) -> list[<ModelReadSchema>]:
        query = (
            select(self.db_model)
            .where(self.db_model.is_active.is_(True))
            .order_by(self.db_model.created_at.desc())
            .limit(limit)
        )
        models = (await self.session.execute(query)).scalars().all()
        return TypeAdapter(list[self.read_schema_type]).validate_python(models)  # type: ignore[name-defined]
```

---

## Queries in separate variables

Always build the query in a named `query` variable before calling `execute()`. This makes multi-step construction (filters, ordering, pagination) readable and avoids nested one-liners that are hard to extend.

```python
# CORRECT
async def get_active_by_status(self, _id: int, status: GenreStatus) -> GenreSchema | None:
    query = (
        select(self.db_model)
        .where(
            self.db_model.id == _id,
            self.db_model.status.in_(
                [GenreStatus.ACTIVE, GenreStatus.PENDING]
            ),
        )
        .limit(1)
    )
    result = await self.session.execute(query)
    return result.scalar_one_or_none()

# WRONG — inline query, hard to read and extend
async def get_active_by_status(self, _id: int, status: GenreStatus) -> GenreSchema | None:
    result = await self.session.execute(select(self.db_model).where(...).limit(1))
    return result.scalar_one_or_none()
```

For conditional filters, build `query` as a base and chain further:

```python
query = select(self.db_model).order_by(self.db_model.created_at.desc())
if status:
    query = query.where(self.db_model.status == status)
```

---

## Result extraction

| Goal | Method |
|---|---|
| Single row, required | `result.scalar_one()` — raises if 0 or >1 rows |
| Single row, optional | `result.scalar_one_or_none()` — returns `None` if not found |
| All rows | `result.scalars().all()` |
| Scalar aggregate | `result.scalar_one()` on `select(func.count(...))` |

Raise `NotFoundError` (from `app.core.exceptions`) when a required record is absent — the base `get_by_id` already does this; follow the same pattern in custom methods.

---

## Partial updates with RETURNING

Use `model_dump(exclude_unset=True)` so only explicitly provided fields are written:

```python
from sqlalchemy import update
from app.apps.<domain>.schemas import <ModelUpdateSchema>

async def partial_update(self, _id: int, data: <ModelUpdateSchema>) ->   <ModelReadSchema>:
    query = (
        update(self.db_model)
        .values(data.model_dump(exclude_unset=True))
        .where(self.db_model.id == _id)
        .returning(self.db_model)
    )
    model = (await self.session.execute(query)).scalar_one()
    return self.read_schema_type.model_validate(model)
```

---

## Loading relationships

No hidden loads. Every relationship attribute the service or response touches must be loaded explicitly in the query that fetches the parent, via `.options(joinedload(...))` or `.options(selectinload(...))`.

Pick the loader by relationship shape and how many parents you load:

| Relationship | Loading context | Use |
|---|---|---|
| many-to-one (to-one) | any | `joinedload` — one round-trip via LEFT OUTER JOIN |
| one-to-many / many-to-many | single parent | `selectinload` |
| one-to-many / many-to-many | multiple parents (lists, paginated) | `selectinload` — avoids row duplication on LIMIT |

**Many-to-one (to-one) — `joinedload`** (one round-trip via LEFT OUTER JOIN):

```python
from sqlalchemy.orm import joinedload

async def get_with_tags(self, _id: int) -> ItemSchema:
    query = (
        select(self.db_model)
        .options(joinedload(self.db_model.tags))
        .where(self.db_model.id == _id)
    )
    result = await self.session.execute(query)
    model = result.scalar_one_or_none()
    if model is None:
        raise NotFoundError(f'Entity with id {_id} not found for model {self.db_model.__name__}')
    return self.read_schema_type.model_validate(model)
```

**Paginated list with a collection — `selectinload`** (avoids row duplication on LIMIT):

```python
from pydantic import TypeAdapter
from sqlalchemy.orm import selectinload, joinedload

async def list_with_relations(self) -> list[ItemSchema]:
    query = (
        select(self.db_model)
        .options(selectinload(self.db_model.tags))       # one-to-many → selectinload
        .options(joinedload(self.db_model.category))     # many-to-one → joinedload
        .order_by(self.db_model.created_at.desc())
    )
    models = (await self.session.execute(query)).scalars().all()
    return TypeAdapter(list[self.read_schema_type]).validate_python(models)  # type: ignore[name-defined]
```

---

## Method naming conventions

| Prefix | Returns | Description |
|---|---|---|
| `get_by_` | `Schema \| None` | Fetch a single optional record |
| `list_` | `list[Schema]` | Fetch multiple records |
| `create` | `Schema` | Insert and return via RETURNING |
| `update` | `Schema` | Mutate and return via RETURNING |
| `delete` | `None` | Delete (base raises if not found first) |

---

## Checklist before submitting

- [ ] Extends `BaseRepositoryImpl[Model, ReadSchema]` with `db_model` and `read_schema_type` set
- [ ] No `self.session.commit()` anywhere in the file
- [ ] Every query built in a named `query` variable
- [ ] Custom list methods use `TypeAdapter(list[self.read_schema_type]).validate_python(...)`
- [ ] Partial update methods use `model_dump(exclude_unset=True)`
- [ ] Relationships loaded via `joinedload` or `selectinload` — never implicit lazy load
- [ ] Return types annotated on every method
- [ ] No business logic in the repository