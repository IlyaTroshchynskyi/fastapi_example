from functools import lru_cache

from faststream.rabbit import RabbitBroker

from app.core.config import get_settings


@lru_cache
def get_broker():
    setting = get_settings()
    return RabbitBroker(setting.MQ_URL)
