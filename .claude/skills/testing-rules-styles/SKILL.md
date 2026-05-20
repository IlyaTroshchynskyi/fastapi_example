---
name: testing-rules-styles
description: Use when writing or reviewing tests in this codebase. Covers API-level testing with AsyncClient, factory usage, mocking boundaries, assertion style, and test naming. Canonical patterns derived from tests/api/.
---

# Testing

**Canonical reference:** `tests/api/test_genres.py` and `tests/api/test_users.py`.

---

## Default: API-Level Tests

**Prefer tests that hit the full stack through HTTP.**

An `AsyncClient` test exercises routes, DI wiring, schema validation, serialization, service logic, repository, and the real database in one shot. Bugs at any layer appear in one test run — no mocking-induced false confidence.

```
tests/
  api/
    test_<domain>.py          # HTTP-level tests (primary)
  services/
    test_<noun>.py            # only for complex isolated logic (e.g. direct S3 operations)
  factory_models/
    factories.py              # polyfactory ModelFactory subclasses
  factory_helpers/
    factories_creators.py     # async DB insert helpers → return schema objects
    factory_getters.py        # async DB query helpers
    factory_updaters.py       # async DB update helpers (add when needed)
```

Unit tests are justified only when a function has complex, self-contained logic worth testing in isolation — like parsing, hashing, or pure validation helpers. If the logic lives in a service method that touches the DB, test it through HTTP.

---

## Test File Structure

One class per endpoint. One method per scenario. Inherit the appropriate base class from `tests/conftest.py`:

| Base class | Provides |
|---|---|
| `TestBaseClientClass` | `self.not_auth_client`, `self.member_client` |
| `TestBaseDBClass` | `self.session` |
| `TestBaseClientDBClass` | All of the above |

```python
from pydantic import TypeAdapter

from tests.conftest import TestBaseClientDBClass
from tests.factory_helpers.factories_creators import create_genres_factory
from tests.factory_models.factories import GenreCreationFactory
from app.apps.genres.schemas import GenreSchema


class TestGetGenres(TestBaseClientDBClass):
    async def test_success(self) -> None:
        genre1 = await create_genres_factory(self.session)
        genre2 = await create_genres_factory(self.session)

        response = await self.member_client.get('/genres')

        assert response.status_code == 200
        assert TypeAdapter(list[GenreSchema]).validate_python(response.json()) == [genre1, genre2]


class TestCreateGenres(TestBaseClientDBClass):
    async def test_success(self) -> None:
        genre_fc = GenreCreationFactory.build()

        response = await self.member_client.post('/genres', json=genre_fc.model_dump())

        assert response.status_code == 201
        assert genre_fc.name == response.json()['name']
```

No `@pytest.mark.asyncio` decorator needed — `asyncio_mode = 'auto'` is set in `pyproject.toml`.

---

## Test Naming

**Never use HTTP status codes in test names.** Name the scenario and expected outcome.

| Don't | Do |
|---|---|
| `test_returns_200` | `test_genres_returned_ordered_by_creation` |
| `test_returns_404` | `test_not_found_when_genre_missing` |
| `test_returns_409` | `test_duplicate_name_rejected` |
| `test_valid_case` | `test_genre_created_with_correct_name` |

Pattern: `test_<subject>_<condition>` or `test_<outcome>_when_<condition>`.

---

## Assertions — Compare Objects, Not Fields

Validate responses by round-tripping through the response schema and comparing objects for all routes that return a body (GET, POST, PUT, PATCH). DELETE endpoints typically return 204 with no body — skip object comparison there.

For `POST`/`PUT` responses, merge server-generated fields into the expected payload. When a subset of fields differ (e.g. timestamps, computed values), use `model_dump(include=...)` or `model_dump(exclude=...)` to scope the comparison to the fields you control. **Every field passed to `exclude=` must be verified in a separate `assert` below** — excluded fields are not forgotten, they are asserted individually.

```python
# GET single — schema round-trip
result = GenreSchema.model_validate(response.json())
assert result == GenreSchema.model_validate(genre_from_db)

# GET list — TypeAdapter round-trip
from pydantic import TypeAdapter
result = TypeAdapter(list[GenreSchema]).validate_python(response.json())
assert result == [genre1, genre2]

# POST/PUT — merge server-generated fields into expected before comparing
actual = response.json()
expected = payload.model_dump(mode='json') | {
    'id': actual['id'],
    'created_at': actual['created_at'],
    'updated_at': actual['updated_at'],
}
assert actual == expected

# When some fields differ, exclude them from bulk comparison …
result = GenreSchema.model_validate(response.json())
expected = GenreSchema.model_validate(db_object)
assert result.model_dump(exclude={'updated_at'}) == expected.model_dump(exclude={'updated_at'})
# … then verify each excluded field individually
assert result.updated_at is not None

# DELETE — no body; just assert the status code
response = await self.member_client.delete(f'/genres/{genre.id}')
assert response.status_code == 204

# Error response — always assert status AND full body
assert response.status_code == 404
assert response.json() == {'detail': 'Entity with id 1 not found for model GenreModel'}

# Avoid field-by-field — hides missing fields, brittle
assert response.json()['name'] == 'Rock'   # bad
```

---

## Test Structure — Separate Setup, Act, and Assert

Every test body must be divided into three blocks separated by blank lines. Do not collapse sections even for trivial tests.

```python
# Good — three clearly separated blocks
async def test_genre_updated_successfully(self) -> None:
    genre = await create_genres_factory(self.session)

    response = await self.member_client.put(f'/genres/{genre.id}', json={'name': 'new'})

    assert response.status_code == 200
    assert response.json()['name'] == 'new'

# Bad — no separation, hard to scan
async def test_genre_updated_successfully(self) -> None:
    genre = await create_genres_factory(self.session)
    response = await self.member_client.put(f'/genres/{genre.id}', json={'name': 'new'})
    assert response.status_code == 200
```

---

## Factories

**Polyfactory `ModelFactory`** for in-memory schema instances — defined in `tests/factory_models/factories.py`:

```python
from polyfactory.factories.pydantic_factory import ModelFactory
from app.apps.genres.schemas import GenreCreateUpdate

class GenreCreationFactory(ModelFactory[GenreCreateUpdate]):
    __model__ = GenreCreateUpdate
```

Usage in tests:
```python
genre_fc = GenreCreationFactory.build()   # in-memory only, no DB write
```

**Factory creator helpers** for DB-persisted records — defined in `tests/factory_helpers/factories_creators.py`. Each helper inserts a record and returns the fully-validated schema object:

```python
async def create_genres_factory(session: AsyncSession) -> GenreSchema:
    genre_fc = GenreCreationFactory.build()
    query = insert(GenreModel).values(**genre_fc.model_dump()).returning(GenreModel)
    genre = await session.scalar(query)
    return GenreSchema.model_validate(genre)
```

Add getter helpers to `factory_getters.py` and update helpers to `factory_updaters.py` following the same pattern. Never define factory helpers inside a test file.

---

## Fixtures

Key fixtures from `tests/conftest.py`:

| Fixture | Scope | Purpose |
|---|---|---|
| `session: AsyncSession` | function | Transactional DB session; rolls back after each test |
| `not_auth_client: AsyncClient` | session | HTTP client with no auth header |
| `member_client: AsyncClient` | session | HTTP client with `Authorization: Bearer token` |
| `_engine: AsyncEngine` | session | Runs Alembic up/down once per test session |
| `mock_broker: AsyncMock` | function | `AsyncMock(spec=RabbitBroker)` — overrides `get_rabbit_broker` |
| `s3_client: S3Client` | function | Real aiobotocore client pointed at Testcontainers MinIO |
| `s3_instance: MinioContainer` | session | MinIO Testcontainer (shared across tests) |

The `session` fixture wraps each test in a transaction rolled back on teardown — tests are fully isolated with no truncation needed.

The `_engine` fixture runs `alembic downgrade base` then `alembic upgrade head` once at session start, ensuring a clean schema.

Domain-level `conftest.py` may add a `setup_data` fixture for prerequisite records:

```python
# tests/api/conftest.py (per-domain)
@pytest.fixture
async def genre(session: AsyncSession) -> GenreSchema:
    return await create_genres_factory(session)
```

---

## What to Mock — and What Not To

**Mock only what you cannot control:** external services that make network calls.

| Boundary | Mock target | Pattern |
|---|---|---|
| RabbitMQ broker | `get_rabbit_broker` dependency | `mock_broker` fixture |
| S3 / MinIO | Real MinIO via Testcontainers | `s3_client` fixture |
| SES email sender | `SesEmailSenderService.send_email` | `patch(..., new_callable=AsyncMock)` |

**Never mock:**
- The database — use the real test DB with transaction rollback
- Repositories — test through them; that's the point
- Your own services — if you need to bypass a service, redesign the test

```python
async def test_user_created_and_message_published(self, mock_broker: AsyncMock) -> None:
    payload = UserCreationFactory.build()

    response = await self.member_client.post('/users', json=payload.model_dump())

    assert response.status_code == 201
    mock_broker.publish.assert_called_once()
```

---

## Unit Tests — When and How

Write a unit test only when a function has complex, self-contained logic that is worth exercising in isolation — e.g., parsing, hashing, transformation, or validation logic that doesn't touch external state.

```python
class TestNormalizeName:
    def test_strips_whitespace(self) -> None:
        result = GenreService._normalize_name('  Rock  ')
        assert result == 'rock'

    def test_lowercases_input(self) -> None:
        result = GenreService._normalize_name('JAZZ')
        assert result == 'jazz'
```

---

## Anti-Patterns

| Pattern | Why It Fails |
|---|---|
| HTTP codes in test names (`test_returns_404`) | Couples tests to transport details |
| Field-by-field assertions | Hides missing fields and allows shape drift without test failures |
| Mocking the database | Creates mock/prod divergence — real migrations may break mocked tests |
| Mocking your own services or repositories | Tests the mock, not the code |
| Missing unauthenticated test | Auth bypass bugs stay hidden |
| Test data defined inside test methods | Can't be reused; clutters the test body — use factory helpers |
| One long test checking multiple scenarios | Hard to diagnose failures — one scenario per test method |
| `@pytest.mark.asyncio` decorator | Not needed — `asyncio_mode = 'auto'` is configured globally |