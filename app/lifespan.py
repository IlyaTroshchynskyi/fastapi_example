import asyncio
from contextlib import asynccontextmanager

from alembic.command import upgrade
from fastapi import FastAPI

from app.core.config import get_settings, Settings
from app.core.database import get_alembic_config
from app.core.enums import Environment
from app.core.infrastructure.brokers.rabbit_broker import get_broker


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await startup(settings)

    broker = get_broker()
    await broker.start()

    app.state.broker = broker

    try:
        yield
    finally:
        await broker.close()


async def run_consumer(settings: Settings): ...


async def startup(settings: Settings) -> None:
    if settings.ENVIRONMENT in (Environment.PRODUCTION, Environment.DEV) and settings.RUN_MIGRATIONS:
        alembic_config = get_alembic_config(get_settings().DATABASE_URL)
        upgrade(alembic_config, 'head')

    if settings.RUN_CONSUMER:
        loop = asyncio.get_running_loop()
        loop.create_task(run_consumer(settings))
