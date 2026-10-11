from polyfactory.factories.pydantic_factory import ModelFactory

from app.apps.genres.schemas import GenreCreateSchema
from app.apps.users.schemas import UserCreateSchema


class GenreCreationFactory(ModelFactory[GenreCreateSchema]):
    __model__ = GenreCreateSchema


class UserCreationFactory(ModelFactory[UserCreateSchema]):
    __model__ = UserCreateSchema
