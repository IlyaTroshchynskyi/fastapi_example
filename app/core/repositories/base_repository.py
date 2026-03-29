from collections.abc import Sequence
from typing import Generic, Protocol, TypeVar

from fastapi import Depends
from pydantic import BaseModel, TypeAdapter
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session, MixinsBase
from app.core.exceptions import NotFoundError

ModelType = TypeVar('ModelType', bound=MixinsBase)
ReadSchemaType = TypeVar('ReadSchemaType', bound=BaseModel)
CreateSchemaType = TypeVar('CreateSchemaType', bound=BaseModel)
UpdateSchemaType = TypeVar('UpdateSchemaType', bound=BaseModel)


class BaseRepositoryProtocol(Protocol[ReadSchemaType]):
    async def get_by_id(self, _id: int) -> ReadSchemaType: ...

    async def get_by_ids(self, ids: Sequence[int]) -> list[ReadSchemaType]: ...

    async def get_all(self) -> list[ReadSchemaType]: ...

    async def create(self, create_object: CreateSchemaType) -> ReadSchemaType: ...

    async def update(self, update_object: UpdateSchemaType, _id: int) -> ReadSchemaType: ...

    async def delete(self, _id: int) -> None: ...


class BaseRepositoryImpl(Generic[ModelType, ReadSchemaType]):
    db_model: type[ModelType]
    read_schema_type: type[ReadSchemaType]

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session

    async def get_by_id(self, _id: int) -> ReadSchemaType:
        query = select(self.db_model).filter(self.db_model.id == _id)
        model = (await self.session.execute(query)).scalar_one_or_none()
        if model is None:
            raise NotFoundError(f'Entity with id {_id} not found for model {self.db_model.__name__}')
        return self.read_schema_type.model_validate(model)

    async def get_by_ids(self, ids: list[int]) -> list[ReadSchemaType]:
        if not ids:
            return []
        query = select(self.db_model).filter(self.db_model.id.in_(ids))
        models = (await self.session.execute(query)).scalars().all()
        return TypeAdapter(list[self.read_schema_type]).validate_python(models)  # type: ignore[name-defined]

    async def get_all(self) -> list[ReadSchemaType]:
        query = select(self.db_model)
        models = (await self.session.execute(query)).scalars().all()
        return TypeAdapter(list[self.read_schema_type]).validate_python(models)  # type: ignore[name-defined]

    async def create(self, create_object: CreateSchemaType) -> ReadSchemaType:
        query = insert(self.db_model).values(**create_object.model_dump()).returning(self.db_model)
        model = (await self.session.execute(query)).scalar_one()
        return self.read_schema_type.model_validate(model)

    async def update(self, update_object: UpdateSchemaType, _id: int) -> ReadSchemaType:
        query = (
            update(self.db_model)
            .values(update_object.model_dump(exclude_unset=True))
            .filter(self.db_model.id == _id)
            .returning(self.db_model)
        )
        model = (await self.session.execute(query)).scalar_one()
        return self.read_schema_type.model_validate(model)

    async def delete(self, _id: int) -> None:
        statement = delete(self.db_model).filter(self.db_model.id == _id).returning(self.db_model)
        await self.session.execute(statement)
