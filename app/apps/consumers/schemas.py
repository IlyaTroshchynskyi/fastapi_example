from enum import StrEnum

from pydantic import BaseModel, EmailStr


class UserCreationStatus(StrEnum):
    SUCCESS = 'success'
    FAILED = 'failed'
    NOT_CONFIRMED = 'not_confirmed'


class UserCreationMsg(BaseModel):
    username: EmailStr
    status: UserCreationStatus
