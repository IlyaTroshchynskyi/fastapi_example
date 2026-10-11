from fastapi import APIRouter, Depends, HTTPException
from faststream.rabbit import RabbitBroker

from app.apps.users.schemas import UserCreateSchema, UserSchema
from app.apps.users.use_cases.register_user import RegisterUserUseCase
from app.core.exceptions import AlreadyExistError
from app.core.infrastructure.brokers.dependencies import get_rabbit_broker

router = APIRouter(tags=['Users'])


@router.post('/users', status_code=201)
async def create_user(
    user_creation: UserCreateSchema,
    register_user_use_case: RegisterUserUseCase = Depends(),
    broker: RabbitBroker = Depends(get_rabbit_broker),
) -> UserSchema:
    try:
        user = await register_user_use_case.execute(user_creation, broker)
    except AlreadyExistError as error:
        raise HTTPException(status_code=409, detail=str(error))
    return user
