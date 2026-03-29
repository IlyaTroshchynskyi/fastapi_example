from fastapi import Depends
from pydantic import EmailStr

from app.apps.users.repository import UserRepository
from app.apps.users.schemas import UserCreateSchema, UserSchema


class UserService:
    def __init__(self, user_repository: UserRepository = Depends()):
        self.user_repository = user_repository

    async def get_user_by_email(self, email: EmailStr) -> UserSchema | None:
        return await self.user_repository.get_user_by_email(email)

    async def create_user(self, user: UserCreateSchema) -> UserSchema:
        return await self.user_repository.create(user)
