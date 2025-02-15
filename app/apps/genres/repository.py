from app.apps.genres.models import GenreModel
from app.core.repositories.base_repository import BaseRepositoryImpl


class GenreRepository(BaseRepositoryImpl):
    db_model = GenreModel
