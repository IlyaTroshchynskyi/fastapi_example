from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GenreCreateSchema(BaseModel):
    name: str = Field(max_length=32)


class GenreCreateUpdate(GenreCreateSchema):
    pass


class GenreSchema(BaseModel):
    id: int
    name: str
    updated_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
