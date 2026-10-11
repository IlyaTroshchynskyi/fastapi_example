from functools import lru_cache

from faststream.rabbit import RabbitBroker

from app.core.config import get_settings


@lru_cache
def get_broker() -> RabbitBroker:
    settings = get_settings()
    return RabbitBroker(settings.MQ_URL)
