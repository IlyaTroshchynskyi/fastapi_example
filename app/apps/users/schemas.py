from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreateSchema(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=32)


class UserSchema(BaseModel):
    id: UUID
    name: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)
