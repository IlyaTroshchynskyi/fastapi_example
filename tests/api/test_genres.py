from pydantic import TypeAdapter

from app.apps.genres.schemas import GenreSchema
from tests.conftest import TestBaseClientDBClass
from tests.factory_models.factories import GenreCreationFactory
from tests.factory_helpers.factories_creators import create_genres_factory


class TestGetGenres(TestBaseClientDBClass):
    async def test_success(self) -> None:
        genre1 = await create_genres_factory(self.session)
        genre2 = await create_genres_factory(self.session)

        response = await self.member_client.get('/genres')

        assert response.status_code == 200
        genres = response.json()
        assert TypeAdapter(list[GenreSchema]).validate_python(genres) == [genre1, genre2]


class TestCreateGenres(TestBaseClientDBClass):
    async def test_success(self) -> None:
        genre_fc = GenreCreationFactory.build()
        response = await self.member_client.post('/genres', json=genre_fc.model_dump())

        assert response.status_code == 201
        assert genre_fc.name == response.json()['name']


class TestGetByIdGenres(TestBaseClientDBClass):
    async def test_success(self) -> None:
        genre1 = await create_genres_factory(self.session)
        await create_genres_factory(self.session)
        response = await self.member_client.get(f'/genres/{genre1.id}')

        assert response.status_code == 200
        assert GenreSchema.model_validate(response.json()) == genre1

    async def test_not_found(self) -> None:
        response = await self.member_client.get('/genres/1')

        assert response.status_code == 404
        assert response.json() == {'detail': 'Entity with id 1 not found for model GenreModel'}


class TestUpdateByIdGenres(TestBaseClientDBClass):
    async def test_success(self) -> None:
        genre1 = await create_genres_factory(self.session)
        await create_genres_factory(self.session)
        response = await self.member_client.put(f'/genres/{genre1.id}', json={'name': 'new'})

        assert response.status_code == 200
        assert response.json()['name'] == 'new'

    async def test_already_exists(self) -> None:
        genre1 = await create_genres_factory(self.session)
        await create_genres_factory(self.session)
        response = await self.member_client.put(f'/genres/{genre1.id}', json={'name': genre1.name})

        assert response.status_code == 409
        assert response.json() == {'detail': 'Genre exists with such name'}

    async def test_not_found(self) -> None:
        response = await self.member_client.put('/genres/1', json={'name': 'new'})

        assert response.status_code == 404
        assert response.json() == {'detail': 'Entity with id 1 not found for model GenreModel'}


class TestDeleteByIdGenres(TestBaseClientDBClass):
    async def test_success(self) -> None:
        response = await self.member_client.delete('/genres/1')

        assert response.status_code == 404
        assert response.json() == {'detail': 'Entity with id 1 not found for model GenreModel'}
