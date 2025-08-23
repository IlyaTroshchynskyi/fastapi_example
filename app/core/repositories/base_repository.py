from collections.abc import Sequence
from typing import Generic, Protocol, TypeVar
import uuid

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, get_session
from app.core.exceptions import NotFoundError

ModelType = TypeVar('ModelType', bound=Base)
ReadSchemaType = TypeVar('ReadSchemaType', bound=BaseModel)
CreateSchemaType = TypeVar('CreateSchemaType', bound=BaseModel)
UpdateSchemaType = TypeVar('UpdateSchemaType', bound=BaseModel)


class BaseRepositoryProtocol(Protocol[ModelType]):
    async def get_by_id(self, _id: int) -> ModelType: ...

    async def get_by_ids(self, ids: Sequence[int]) -> list[ModelType]: ...

    async def get_all(self) -> list[ModelType]: ...

    async def create(self, create_object: CreateSchemaType) -> ModelType: ...

    async def update(self, update_object: UpdateSchemaType) -> ModelType: ...

    async def delete(self, _id: uuid.UUID) -> None: ...


class BaseRepositoryImpl(Generic[ModelType]):
    db_model: type[ModelType]

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session

    async def get_by_id(self, _id: int) -> ModelType:
        query = select(self.db_model).filter(_id == self.db_model.id)
        model = (await self.session.execute(query)).scalar_one_or_none()
        if model is None:
            raise NotFoundError(f'Entity with id {_id} not found for model {self.db_model.__name__}')
        return model

    async def get_by_ids(self, ids: list[int]) -> Sequence[ModelType]:
        query = select(self.db_model).where(self.db_model.id.in_(ids))
        models = (await self.session.execute(query)).scalars().all()
        return models

    async def get_all(self) -> Sequence[ModelType]:
        query = select(self.db_model)
        models = (await self.session.execute(query)).scalars().all()
        return models

    async def create(self, create_object: CreateSchemaType) -> ModelType:
        query = insert(self.db_model).values(**create_object.model_dump()).returning(self.db_model)
        model = (await self.session.execute(query)).scalar_one()
        return model

    async def update(self, update_object: UpdateSchemaType, _id: int) -> ModelType:
        query = (
            update(self.db_model)
            .values(update_object.model_dump(exclude_unset=True))
            .filter(_id == self.db_model.id)
            .returning(self.db_model)
        )
        model = (await self.session.execute(query)).scalar_one()
        return model

    async def delete(self, _id: int) -> None:
        statement = delete(self.db_model).filter(_id == self.db_model.id).returning(self.db_model)
        await self.session.execute(statement)
