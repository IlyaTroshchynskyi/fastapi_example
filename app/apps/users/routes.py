from fastapi import APIRouter, Depends, HTTPException
from faststream.rabbit import RabbitBroker

from app.apps.users.schemas import UserCreateSchema, UserSchema
from app.apps.users.use_cases.register_user import RegisterUserUseCase
from app.core.exceptions import AlreadyExistError
from app.core.infrastructure.brokers.dependencies import get_rabbit_broker

router = APIRouter(tags=['Users'])


@router.post('/users', status_code=201)
async def create_users(
    user_creation: UserCreateSchema,
    service: RegisterUserUseCase = Depends(),
    broker: RabbitBroker = Depends(get_rabbit_broker),
) -> UserSchema:
    try:
        user = await service.execute(user_creation, broker)
    except AlreadyExistError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return user
