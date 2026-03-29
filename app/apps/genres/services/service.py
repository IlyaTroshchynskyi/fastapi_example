from typing import Annotated

from fastapi import Depends

from app.apps.genres.repository import GenreRepository
from app.apps.genres.schemas import GenreCreateUpdate, GenreSchema
from app.core.exceptions import AlreadyExistError


class GenreService:
    def __init__(self, genre_repository: Annotated[GenreRepository, Depends(GenreRepository)]):
        self.genre_repository = genre_repository

    async def get_all_genres(self) -> list[GenreSchema]:
        return await self.genre_repository.get_all()

    async def get_genre_by_id(self, _id: int) -> GenreSchema:
        return await self.genre_repository.get_by_id(_id)

    async def create_genre(self, genre: GenreCreateUpdate) -> GenreSchema:
        return await self.genre_repository.create(genre)

    async def update_genre(self, genre: GenreCreateUpdate, _id: int) -> GenreSchema:
        current_genre = await self.get_genre_by_id(_id)
        if current_genre.name == genre.name:
            raise AlreadyExistError('Genre exists with such name')

        return await self.genre_repository.update(genre, _id)

    async def delete_genre(self, _id: int) -> None:
        await self.genre_repository.get_by_id(_id)
        await self.genre_repository.delete(_id)
