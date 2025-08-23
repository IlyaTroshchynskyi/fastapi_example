from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.genres.models import GenreModel
from app.apps.genres.schemas import GenreSchema
from tests.factory_models.factories import GenreCreationFactory


async def create_genres_factory(
    session: AsyncSession,
) -> GenreSchema:
    genre_fc = GenreCreationFactory.build()
    query = insert(GenreModel).values(**genre_fc.model_dump()).returning(GenreModel)
    genre = await session.scalar(query)
    return GenreSchema.model_validate(genre)
