from functools import lru_cache

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.enums import Environment


class Settings(BaseSettings):
    PROJECT_NAME: str = 'name'
    ROOT_PATH: str = '/path'  # need for api gateway
    ENVIRONMENT: Environment = Environment.LOCAL
    RUN_CONSUMER: bool = True

    DATABASE_URL: PostgresDsn

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_DEFAULT_REGION: str

    RUN_MIGRATIONS: bool = False

    model_config = SettingsConfigDict(
        case_sensitive=True,
        frozen=True,
        env_file='.env',
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
