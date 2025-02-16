import uuid

from sqlalchemy import func, String, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import MixinsBase


class UserModel(MixinsBase):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(32))
