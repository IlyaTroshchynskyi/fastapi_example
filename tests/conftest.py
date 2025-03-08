from asyncio import DefaultEventLoopPolicy
import os
import pathlib
from typing import AsyncIterable, AsyncGenerator, Generator

from alembic.command import downgrade, upgrade
from botocore.exceptions import ClientError
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncEngine, AsyncSession, create_async_engine
from testcontainers.minio import MinioContainer
from types_aiobotocore_s3 import S3Client

from app.core.aws_boto_clients import get_aioboto_session, open_s3_client
from app.core.config import get_settings
from tests.dependencies import override_app_test_dependencies, override_dependency

TEST_HOST = 'http://test'


def pytest_configure(config: pytest.Config):
    """
    Allows plugins and conftest files to perform initial configuration.
    This hook is called for every plugin and initial conftest
    file after command line options have been parsed.
    """
    os.environ['ENVIRONMENT'] = 'dev'
    os.environ['DATABASE_URL'] = 'postgresql+psycopg://test_postgres:test_postgres@localhost:5437/example-test'

    os.environ['AWS_ACCESS_KEY_ID'] = 'key'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'key'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-central-1'

    os.environ['S3_LOCAL_HOST'] = 'http://127.0.0.1:9000'
    os.environ['S3_BUCKET'] = 'test'
    os.environ['LOCAL_AWS_ACCESS_KEY_ID'] = 'access_key'
    os.environ['LOCAL_AWS_SECRET_ACCESS_KEY'] = 'secret_key'


@pytest.fixture(scope='session')
async def app() -> FastAPI:
    from app.main import create_app

    _app = create_app()
    override_app_test_dependencies(_app)

    yield _app


@pytest.fixture(scope='session')
async def not_auth_client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=TEST_HOST) as client:
        yield client


@pytest.fixture(scope='session')
async def member_client(app: FastAPI) -> AsyncClient:
    token = 'token'
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=TEST_HOST, headers={'Authorization': f'Bearer {token}'}
    ) as client:
        yield client


@pytest.fixture(scope='function')
async def session(app: FastAPI, _engine: AsyncEngine) -> AsyncIterable[AsyncSession]:
    connection = await _engine.connect()
    trans = await connection.begin()

    session_factory = async_sessionmaker(connection, expire_on_commit=False)
    session = session_factory()

    from app.core.database import get_session

    override_dependency(app, get_session, lambda: session)

    try:
        yield session
    finally:
        await trans.rollback()
        await session.close()
        await connection.close()


@pytest.fixture(scope='session', autouse=True)
async def _engine() -> AsyncIterable[AsyncEngine]:
    settings = get_settings()

    from app.core.database import get_alembic_config

    alembic_config = get_alembic_config(settings.DATABASE_URL, script_location=find_migrations_script_location())

    engine = create_async_engine(settings.DATABASE_URL.unicode_string())
    async with engine.begin() as connection:
        await connection.run_sync(lambda conn: downgrade(alembic_config, 'base'))
        await connection.run_sync(lambda conn: upgrade(alembic_config, 'head'))

    try:
        yield engine
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(lambda conn: downgrade(alembic_config, 'base'))
        await engine.dispose()


def find_migrations_script_location() -> str:
    """Help find script location if tests was run by debugger or any other way except writing 'pytest' in cli"""
    return os.path.join(pathlib.Path(os.path.dirname(os.path.realpath(__file__))).parent, 'migrations')


@pytest.fixture(scope='session', params=(DefaultEventLoopPolicy(),))
def event_loop_policy(request):
    return request.param


class TestBaseDBClass:
    """Provides Test Class with loaded database fixture"""

    @pytest.fixture(autouse=True)
    def _a_provide_session(self, session: AsyncSession):
        """
        Provides a database for all tests in class.
        The 'a' letter in the name required for loading these fixtures first, it's not good but ok for now.
        """
        self.session = session


class TestBaseClientClass:
    """Provides Test Class with loaded client fixture"""

    @pytest.fixture(autouse=True)
    def _a_provide_client(
        self,
        not_auth_client: AsyncClient,
        member_client: AsyncClient,
    ):
        """
        Provides a client for all tests in class.
        The 'a' letter in the name required for loading these fixtures first, it's not good but ok for now.
        """
        self.not_auth_client = not_auth_client
        self.member_client = member_client


class TestBaseClientDBClass(TestBaseClientClass, TestBaseDBClass):
    """Provides Test Class with loaded database and client fixture"""


async def delete_all_objects(s3: S3Client, bucket_name: str):
    response = await s3.list_objects_v2(Bucket=bucket_name)
    if 'Contents' in response:
        objects = [{'Key': obj['Key']} for obj in response['Contents']]
        await s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})


@pytest.fixture(scope='session')
def s3_instance() -> Generator[MinioContainer, None, None]:
    with MinioContainer(access_key='access_key', secret_key='access_key') as minio:
        minio_client = minio.get_client()
        minio_client.make_bucket(os.environ['S3_BUCKET'])
        yield minio


@pytest.fixture(scope='function')
async def s3_client(s3_instance) -> AsyncGenerator[S3Client, None]:
    session = get_aioboto_session()
    async with (
        open_s3_client(session=session, settings=get_settings()) as s3_client,
    ):
        try:
            await delete_all_objects(s3_client, os.environ['S3_BUCKET'])
        except ClientError:
            pass
        yield s3_client
