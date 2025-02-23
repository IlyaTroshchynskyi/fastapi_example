from fastapi import Depends

from app.apps.users.schemas import UserCreateSchema, UserSchema
from app.apps.users.services.service import UserService
from app.core.exceptions import AlreadyExistError
from app.core.schemas import EmailMessage
from app.core.services.ses import SesEmailSenderService


class RegisterUserUseCase:
    def __init__(
        self,
        user_service: UserService = Depends(),
        notification_service: SesEmailSenderService = Depends(),
    ):
        self._user_service = user_service
        self._notification_service = notification_service

    async def execute(self, user_data: UserCreateSchema) -> UserSchema:
        existing_user = await self._user_service.get_user_by_email(user_data.email)
        if existing_user:
            raise AlreadyExistError('Email is already registered')

        new_user = await self._user_service.create_user(user_data)

        await self._notification_service.send_email(
            EmailMessage(target_email=new_user.email, subject='subject', body='text')
        )
        return new_user
