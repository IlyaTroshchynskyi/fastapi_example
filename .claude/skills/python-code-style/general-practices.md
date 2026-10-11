# General Python Practices — Code Examples

Examples for the rules stated in `SKILL.md`. The rules themselves live there; this file only illustrates them.

## Type Hints

### Type Narrowing

```python
# Good — type checker knows genre is GenreSchema after the guard
async def get_genre_by_name(self, name: str) -> GenreSchema:
    genre = await self.genre_repository.find_by_name(name)
    if genre is None:
        raise NotFoundError(f'Genre with name {name} not found')
    # here: genre is GenreSchema, not GenreSchema | None
    return genre

# Filter None from a list — result is narrowed to list[GenreSchema]
valid_genres = [genre for genre in genres if genre is not None]
```

### Generics and TypeVar

```python
from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T')
ModelT = TypeVar('ModelT', bound=BaseModel)

# Bound TypeVar — restricts to BaseModel subclasses
def parse_model(model_class: type[ModelT], fields: dict[str, object]) -> ModelT:
    return model_class.model_validate(fields)

# Usage — genre is typed as GenreSchema, not BaseModel
genre = parse_model(GenreSchema, {'id': 1, 'name': 'Rock'})
```

## Early Returns

```python
# Good
async def update_genre(self, genre_update: GenreUpdateSchema, _id: int) -> GenreSchema:
    current_genre = await self.get_genre_by_id(_id)
    if current_genre.name == genre_update.name:
        raise AlreadyExistError('Genre exists with such name')
    return await self.genre_repository.update(genre_update, _id)

# Bad — nesting delays the error path
async def update_genre(self, genre_update: GenreUpdateSchema, _id: int) -> GenreSchema:
    current_genre = await self.get_genre_by_id(_id)
    if current_genre.name != genre_update.name:
        return await self.genre_repository.update(genre_update, _id)
    else:
        raise AlreadyExistError('Genre exists with such name')
```
