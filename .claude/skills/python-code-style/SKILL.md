---
name: python-code-style
description: Use when writing, reviewing, or modifying any Python code in this codebase. Canonical style rules for services, routers, schemas, repositories, and tests. Prerequisite for fastapi-service.
---

# Python Code Style

Rules for writing production-quality Python in this codebase. Every rule reflects a deliberate choice; follow them unless you have a specific, stated reason not to.

> Target: **Python 3.12**. Use builtin generics (`list[int]`, `dict[str, int]`, `str | None`) — never `List`, `Dict`, `Optional`, `Union` from `typing`. Use `typing` only for types without builtin equivalents: `Annotated`, `TypeAlias`, `Literal`, `TypeVar`, `Generic`, `TypedDict`, `TYPE_CHECKING`. Prefer Abstract Classes over `Protocol` for new interfaces (see below); `Protocol` is used in the existing codebase for `BaseRepositoryProtocol`.

**Related skills:** `fastapi-service`, `create-repository`.

---

## Type Hints

Type every public function, method, and class attribute. Types are documentation the toolchain can verify.

**Never use `Any`** unless the value is genuinely unconstrained. Reaching for `Any` means you don't know the type — stop and find it. `Any` silently disables type checking for everything it touches.

```python
class GenreService:
    def __init__(
        self,
        genre_repository: Annotated[GenreRepository, Depends(GenreRepository)],
    ) -> None:
        self.genre_repository = genre_repository

    async def get_genre_by_id(self, _id: int) -> GenreSchema | None:
        ...
```

### Type Narrowing

Use early returns or guards to narrow `X | None` before use. The type checker tracks narrowed types through the rest of the scope.

```python
# Good — type checker knows genre is GenreSchema after the guard
async def get_genre_by_id(self, _id: int) -> GenreSchema | None:
    genre = await self.genre_repository.get_by_id(_id)
    if genre is None:
        raise NotFoundError(f'Genre with id {_id} not found')
    # here: genre is GenreSchema, not GenreSchema | None
    return genre

# Filter None from a list — result is narrowed to list[GenreSchema]
valid_genres = [g for g in genres if g is not None]
```

### Type Aliases

Create meaningful names for complex types. Use `TypeAlias` (Python 3.10+) — never the `type X = ...` statement syntax (that requires Python 3.12).

```python
from typing import TypeAlias
from collections.abc import Callable, Awaitable

AsyncHandler: TypeAlias = Callable[[Request], Awaitable[Response]]
```

### Generics and TypeVar

Use `TypeVar` + `Generic` when writing reusable containers or helpers that must preserve the type of their contents.

```python
from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T')
ModelT = TypeVar('ModelT', bound=BaseModel)

# Bound TypeVar — restricts to BaseModel subclasses
def validate_and_create(model_cls: type[ModelT], data: dict) -> ModelT:
    return model_cls.model_validate(data)

# Usage — genre is typed as GenreSchema, not BaseModel
genre = validate_and_create(GenreSchema, {'id': 1, 'name': 'Rock'})
```

---

## Abstract Classes — Preferred Over Protocols

**Use `ABC` + `@abstractmethod` for all new interfaces.** `Protocol` already exists in the codebase (`BaseRepositoryProtocol`) and is acceptable there, but prefer ABC for new contracts.

ABC provides nominal typing: subclasses must explicitly inherit and implement every abstract method. Python raises `TypeError` at instantiation time if any abstract method is left unimplemented — you catch the error at the class definition boundary, not at the call site.

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic

T = TypeVar('T')
ID = TypeVar('ID')

class BaseRepository(ABC, Generic[T, ID]):
    """Abstract base for all repositories."""

    @abstractmethod
    async def get_by_id(self, id: ID) -> T | None: ...

    @abstractmethod
    async def create(self, entity: T) -> T: ...

    @abstractmethod
    async def delete(self, id: ID) -> None: ...


class GenreRepository(BaseRepository[GenreSchema, int]):
    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        self.session = session

    async def get_by_id(self, id: int) -> GenreSchema | None:
        query = select(GenreModel).where(GenreModel.id == id)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return GenreSchema.model_validate(model) if model else None

    async def create(self, entity: GenreSchema) -> GenreSchema:
        ...

    async def delete(self, id: int) -> None:
        ...
```

**Why ABC over Protocol:**
- Nominal inheritance makes the contract explicit and IDE-navigable
- `TypeError` fires at class definition if an abstract method is missing — fail-fast
- Easier to mock in tests (subclass, implement the methods you need)
- Supports the template method pattern (partial implementations with `super()`)

**Use ABC when:** defining a shared contract for multiple concrete implementations (repositories, integrations, external service clients).

---

## Async vs Sync

**Use `async def` when the function:**
- Executes any database query (`await session.execute(...)`)
- Calls any external service (S3, RabbitMQ, SES, HTTP APIs)
- Calls another `async def` — async is contagious up the call chain
- Is a FastAPI route handler (always `async`)

**Use plain `def` when the function:**
- Does pure computation — no I/O, no `await` anywhere in the body
- Is a `@staticmethod` helper doing CPU work (parsing, hashing, validation)
- Is a Pydantic validator or `@property`

```python
# async — touches the DB
async def get_all_genres(self) -> list[GenreSchema]:
    return await self.genre_repository.get_all()

# sync — pure computation, no I/O
@staticmethod
def _normalize_name(raw: str) -> str:
    return raw.strip().lower()
```

**Never:**
- Call `time.sleep()` inside `async def` — use `await asyncio.sleep()` instead
- Run blocking I/O (file read, `requests.get`) inside an `async def` — it freezes the entire event loop
- Use the synchronous SQLAlchemy API (`Session`) inside FastAPI routes — always use `AsyncSession`

---

## Model-First Data

Always use a data model (`BaseModel`, `dataclass`, `TypedDict`) for structured data. Never pass raw `dict` when the shape is known.

```python
# Good
class EmailMessage(BaseModel):
    target_email: str
    subject: str
    body: str

# Bad — shape is known but caller passes raw dict
async def send_email(self, data: dict) -> None: ...
```

---

## Enumerate Known Values

When a value comes from a predefined set, use `StrEnum` or `Literal` — never a bare `str`.

```
Small, local, one field?                → Literal
Reused across modules, > 3 values?     → StrEnum
```

All enums live in **`app/core/enums.py`** (project-wide) or the domain's `enums.py` — never inline in `schemas.py` or `models.py`.

```python
from enum import StrEnum

class UserCreationStatus(StrEnum):
    SUCCESS = 'success'
    FAILED = 'failed'
    PENDING = 'pending'
```

`StrEnum` members compare equal to their string value — useful for JSON round-trips.

---

## Class Layout

Public interface first, private implementation after. Callers see the contract immediately.

```python
class GenreService:
    # 1. __init__
    def __init__(self, ...) -> None: ...

    # 2. public async methods  ← business API
    async def get_all_genres(self, ...) -> list[GenreSchema]: ...
    async def create_genre(self, ...) -> GenreSchema: ...

    # ── private helpers below ──────────────────────────────
    # 3. private instance methods
    async def _validate_unique_name(self, name: str) -> None: ...

    # 4. static helpers — always at the BOTTOM
    @staticmethod
    def _normalize_name(raw: str) -> str: ...
```

Module-level constants go **above** the class, never embedded in methods:

```python
MAX_GENRE_NAME_LENGTH = 32
DEFAULT_PAGE_SIZE = 20
```

---

## Early Returns

Exit the function the moment you know the answer. Never nest the happy path inside `if not error`.

```python
# Good
async def update_genre(self, genre: GenreCreateUpdate, _id: int) -> GenreSchema:
    current = await self.get_genre_by_id(_id)
    if current.name == genre.name:
        raise AlreadyExistError('Genre exists with such name')
    return await self.genre_repository.update(genre, _id)

# Bad — nesting delays the error path
async def update_genre(self, genre: GenreCreateUpdate, _id: int) -> GenreSchema:
    current = await self.get_genre_by_id(_id)
    if current.name != genre.name:
        return await self.genre_repository.update(genre, _id)
    else:
        raise AlreadyExistError('Genre exists with such name')
```

---

## Fail Fast, Fail Loud

- Raise specific domain exceptions at the first violation — never return `None` as an error signal
- Never swallow errors with `except Exception: pass`
- Chain exceptions: `raise DomainError(...) from exc` to preserve cause
- Never log sensitive user data — log opaque IDs (`user_id`, `genre_id`), never names, emails, or raw payloads

```python
# Good
try:
    await self._s3_client.upload(key, content)
except ClientError as exc:
    raise ServiceError(f'S3 upload failed for key {key}') from exc

# Bad — hides the cause
try:
    await self._s3_client.upload(key, content)
except Exception:
    pass
```

---

## Dependency Injection

Inject every collaborator through the constructor. Never instantiate services, repositories, or clients inside a class body.

In this project, DI is wired via `Annotated[..., Depends(...)]` directly in service `__init__` — no separate `dependencies.py` file per domain.

```python
# Good — DI through constructor
class GenreService:
    def __init__(
        self,
        genre_repository: Annotated[GenreRepository, Depends(GenreRepository)],
    ) -> None:
        self.genre_repository = genre_repository

# Bad — hidden coupling, untestable
class GenreService:
    def __init__(self) -> None:
        self.genre_repository = GenreRepository()
```

---

## Self-Documenting Code

Name things so the code reads like the business domain. Comments explain *why*, never *what*.

```python
# Good name — no comment needed
async def _validate_unique_genre_name(self, name: str) -> None: ...

# Narrates the obvious
# Check if genre exists
existing = await self.genre_repository.get_by_name(name)
```

**Do comment the non-obvious:**

```python
# No retry: if broker publish fails, the DB transaction still commits.
# The consumer is idempotent and handles re-delivery from the dead-letter queue.
await broker.publish(msg, self._settings.MQ_QUEUE_NAME, exchange)
```

---

## Docstrings

Keep docstrings to a **single short line** describing what the function does. Do **not** add `Args:`, `Returns:`, or `Raises:` sections — well-named type hints and variable names already communicate that information.

```python
# Good
async def get_genre_by_id(self, _id: int) -> GenreSchema:
    """Fetch a single genre by primary key, raising NotFoundError if absent."""

# Bad — verbose, duplicates type hints
async def get_genre_by_id(self, _id: int) -> GenreSchema:
    """Fetch a single genre by primary key, raising NotFoundError if absent.

    Args:
        _id: Primary key of the genre.
    Returns:
        GenreSchema with all fields populated.
    Raises:
        NotFoundError: If the genre does not exist.
    """
```

---

## Size Limits

- **Functions:** 50 lines max. If a function exceeds this, extract private helpers.
- **Files:** 800 lines max. If a file exceeds this, split by responsibility.

---

## No Utils Modules

Never create `utils.py`, `helpers.py`, `common.py`. These grow into maintenance traps.

Every function belongs somewhere specific:
- Business logic → `app/apps/<domain>/services/service.py`
- Framework/cross-cutting → `app/core/`

---

Incremental adoption checklist:
- [ ] All function parameters annotated
- [ ] All return types annotated
- [ ] Class attributes annotated in `__init__`
- [ ] No bare `list` / `dict` — always parametrize: `list[str]`, `dict[str, int]`
- [ ] `Any` only where third-party types are genuinely unavailable

---

## Architecture Principles

Priority order — apply the first applicable rule:

1. **KISS** — simple, readable solutions over clever ones
2. **YAGNI** — don't build for hypothetical future needs
3. **Single Responsibility** — one class, one reason to change
4. **DRY** — wait for the third repetition before abstracting
5. **Encapsulation** — hide internal state (`_` prefix), expose behaviour
6. **Fail Fast** — validate at boundaries, never swallow errors

---

## Red Flags — STOP

| About to… | Rule to apply |
|---|---|
| Type `Any` because "the shape is complex" | Type Hints — find the real type |
| Define a new interface without inheriting `ABC` | Abstract Classes — nominal typing required |
| Pass `dict` to a method whose shape is known | Model-First Data |
| Use a bare `str` for a fixed set of values | Enumerate Known Values — use `StrEnum` |
| Put `time.sleep()` inside `async def` | Async vs Sync — use `asyncio.sleep()` |
| Call `requests.get()` or blocking I/O inside `async def` | Async vs Sync — use an async client |
| Use `Session` (sync) instead of `AsyncSession` | Async vs Sync — always async in FastAPI |
| Instantiate `Repository` or service inside a class | Dependency Injection — inject via constructor |
| Write `except Exception: pass` | Fail Fast — never swallow errors |
| Create `utils.py` / `helpers.py` | No Utils Modules — find the right home |
| Put private methods before `__init__` or public methods | Class Layout — public API first |
| Embed a magic number inside a method body | Module-Level Constants — define above the class |
| Log sensitive user data (email, name, payload) | Fail Fast — log opaque IDs only |
| Add a comment that narrates what the next line does | Self-Documenting Code — rename instead |
| Use bare `list` / `dict` in a type annotation | Generics — always parametrize: `list[str]`, `dict[str, int]` |
| Write `type X = ...` syntax | Type Aliases — use `TypeAlias` (`type X = ...` is Python 3.12+ new syntax — avoid for consistency) |