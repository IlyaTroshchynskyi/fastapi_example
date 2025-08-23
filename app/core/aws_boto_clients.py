from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncGenerator

from aiobotocore.session import AioSession, get_session
from fastapi import Depends
from types_aiobotocore_s3 import S3Client

from app.core.config import get_settings, Settings
from app.core.enums import Environment


@lru_cache
def get_aioboto_session() -> AioSession:
    return get_session()


async def get_s3_client(
    session: AioSession = Depends(get_aioboto_session), settings: Settings = Depends(get_settings)
) -> AsyncGenerator[S3Client, None]:
    """FastAPI Dependency"""
    async with open_s3_client(session, settings) as client:
        yield client


@asynccontextmanager
async def open_s3_client(session: AioSession, settings: Settings) -> AsyncGenerator[S3Client, None]:
    if settings.ENVIRONMENT is Environment.DEV:
        params = {
            'endpoint_url': settings.S3_LOCAL_HOST,
            'aws_access_key_id': settings.LOCAL_AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.LOCAL_AWS_SECRET_ACCESS_KEY,
        }
    else:
        params = {
            'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
        }

    async with session.create_client('s3', region_name=settings.AWS_DEFAULT_REGION, **params) as client:  # type: ignore
        yield client
