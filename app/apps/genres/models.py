from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import MixinsBase


class GenreModel(MixinsBase):
    __tablename__ = 'genres'

    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)
