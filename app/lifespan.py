import asyncio
from contextlib import asynccontextmanager

from alembic.command import upgrade
from fastapi import FastAPI

from app.core.config import get_settings, Settings
from app.core.database import get_alembic_config
from app.core.enums import Environment


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await startup(settings)
    yield


async def run_consumer(settings: Settings): ...


async def startup(settings: Settings) -> None:
    if settings.ENVIRONMENT in (Environment.PRODUCTION, Environment.DEV) and settings.RUN_MIGRATIONS:
        alembic_config = get_alembic_config(get_settings().DATABASE_URL)
        upgrade(alembic_config, 'head')

    if settings.RUN_CONSUMER is True:
        loop = asyncio.get_running_loop()
        loop.create_task(run_consumer(settings))
