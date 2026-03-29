from pydantic import EmailStr
from sqlalchemy import select

from app.apps.users.models import UserModel
from app.apps.users.schemas import UserSchema
from app.core.repositories.base_repository import BaseRepositoryImpl


class UserRepository(BaseRepositoryImpl[UserModel, UserSchema]):
    db_model = UserModel
    read_schema_type = UserSchema

    async def get_user_by_email(self, email: EmailStr) -> UserSchema | None:
        query = select(UserModel).filter_by(email=email)
        model = (await self.session.execute(query)).scalar_one_or_none()
        if model is None:
            return None
        return self.read_schema_type.model_validate(model)
