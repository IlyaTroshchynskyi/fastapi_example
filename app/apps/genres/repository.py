from app.apps.genres.models import GenreModel
from app.apps.genres.schemas import GenreSchema
from app.core.repositories.base_repository import BaseRepositoryImpl


class GenreRepository(BaseRepositoryImpl[GenreModel, GenreSchema]):
    db_model = GenreModel
    read_schema_type = GenreSchema
