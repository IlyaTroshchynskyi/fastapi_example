from fastapi import APIRouter, Depends, HTTPException

from app.apps.users.schemas import UserCreateSchema, UserSchema
from app.apps.users.use_cases.register_user import RegisterUserUseCase
from app.core.exceptions import AlreadyExistError

router = APIRouter(tags=['Users'])


@router.post('/users', status_code=201)
async def create_users(user_data: UserCreateSchema, service: RegisterUserUseCase = Depends()) -> UserSchema:
    try:
        user = await service.execute(user_data)
    except AlreadyExistError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return user
