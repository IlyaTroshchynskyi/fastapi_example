from pydantic import TypeAdapter

from app.apps.genres.schemas import GenreSchema
from tests.conftest import TestBaseClientDBClass
from tests.factory_helpers.factories_creators import create_genre
from tests.factory_models.factories import GenreCreationFactory


class TestGetGenres(TestBaseClientDBClass):
    async def test_all_genres_returned(self) -> None:
        earlier_genre = await create_genre(self.session)
        later_genre = await create_genre(self.session)

        response = await self.member_client.get('/genres')

        assert response.status_code == 200
        genres = response.json()
        assert TypeAdapter(list[GenreSchema]).validate_python(genres) == [earlier_genre, later_genre]


class TestCreateGenres(TestBaseClientDBClass):
    async def test_created_genre_returned(self) -> None:
        genre_creation = GenreCreationFactory.build()

        response = await self.member_client.post('/genres', json=genre_creation.model_dump())

        assert response.status_code == 201
        assert genre_creation.name == response.json()['name']


class TestGetByIdGenres(TestBaseClientDBClass):
    async def test_genre_returned_by_id(self) -> None:
        requested_genre = await create_genre(self.session)
        await create_genre(self.session)

        response = await self.member_client.get(f'/genres/{requested_genre.id}')

        assert response.status_code == 200
        assert GenreSchema.model_validate(response.json()) == requested_genre

    async def test_not_found_when_genre_missing(self) -> None:
        response = await self.member_client.get('/genres/1')

        assert response.status_code == 404
        assert response.json() == {'detail': 'Entity with id 1 not found for model GenreModel'}


class TestUpdateByIdGenres(TestBaseClientDBClass):
    async def test_genre_renamed(self) -> None:
        genre = await create_genre(self.session)
        await create_genre(self.session)

        response = await self.member_client.put(f'/genres/{genre.id}', json={'name': 'new'})

        assert response.status_code == 200
        assert response.json()['name'] == 'new'

    async def test_unchanged_name_rejected(self) -> None:
        genre = await create_genre(self.session)
        await create_genre(self.session)

        response = await self.member_client.put(f'/genres/{genre.id}', json={'name': genre.name})

        assert response.status_code == 409
        assert response.json() == {'detail': 'Genre exists with such name'}

    async def test_not_found_when_genre_missing(self) -> None:
        response = await self.member_client.put('/genres/1', json={'name': 'new'})

        assert response.status_code == 404
        assert response.json() == {'detail': 'Entity with id 1 not found for model GenreModel'}


class TestDeleteByIdGenres(TestBaseClientDBClass):
    async def test_not_found_when_genre_missing(self) -> None:
        response = await self.member_client.delete('/genres/1')

        assert response.status_code == 404
        assert response.json() == {'detail': 'Entity with id 1 not found for model GenreModel'}
