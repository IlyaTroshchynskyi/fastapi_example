from sqlalchemy import select

from app.apps.users.models import UserModel
from app.core.repositories.base_repository import BaseRepositoryImpl


class UserRepository(BaseRepositoryImpl):
    db_model = UserModel

    async def get_user_by_email(self, email) -> UserModel | None:
        query = select(UserModel).filter_by(email=email)
        return (await self.session.execute(query)).scalar_one_or_none()
