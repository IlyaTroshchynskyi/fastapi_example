from polyfactory.factories.pydantic_factory import ModelFactory

from app.apps.genres.schemas import GenreCreateUpdate


class GenreCreationFactory(ModelFactory[GenreCreateUpdate]):
    __model__ = GenreCreateUpdate
