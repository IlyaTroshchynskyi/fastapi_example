from polyfactory.factories.pydantic_factory import ModelFactory

from app.apps.genres.schemas import GenreCreateUpdate
from app.apps.users.schemas import UserCreateSchema


class GenreCreationFactory(ModelFactory[GenreCreateUpdate]):
    __model__ = GenreCreateUpdate


class UserCreationFactory(ModelFactory[UserCreateSchema]):
    __model__ = UserCreateSchema
