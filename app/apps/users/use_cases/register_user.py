from fastapi import Depends
from faststream.rabbit import RabbitBroker

from app.apps.consumers.exchanges import build_user_creation_exchange
from app.apps.consumers.schemas import UserCreationMessage, UserCreationStatus
from app.apps.users.schemas import UserCreateSchema, UserSchema
from app.apps.users.services.service import UserService
from app.core.config import get_settings, Settings
from app.core.exceptions import AlreadyExistError
from app.core.schemas import EmailMessage
from app.core.services.ses import SesEmailSenderService


class RegisterUserUseCase:
    def __init__(
        self,
        user_service: UserService = Depends(),
        notification_service: SesEmailSenderService = Depends(),
        settings: Settings = Depends(get_settings),
    ):
        self._user_service = user_service
        self._notification_service = notification_service
        self._settings = settings

    async def execute(self, user_creation: UserCreateSchema, broker: RabbitBroker) -> UserSchema:
        existing_user = await self._user_service.find_user_by_email(user_creation.email)
        if existing_user:
            raise AlreadyExistError('Email is already registered')

        new_user = await self._user_service.create_user(user_creation)

        await self._notification_service.send_email(
            EmailMessage(target_email=new_user.email, subject='subject', body='text')
        )
        await self._publish_user_creation_message(broker, user_creation)
        return new_user

    async def _publish_user_creation_message(self, broker: RabbitBroker, user_creation: UserCreateSchema) -> None:
        message = UserCreationMessage(username=user_creation.email, status=UserCreationStatus.SUCCESS)
        exchange = build_user_creation_exchange()
        await broker.publish(message, self._settings.MQ_QUEUE_NAME, exchange)
