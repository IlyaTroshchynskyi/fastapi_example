from faststream.rabbit import ExchangeType, RabbitExchange

from app.core.config import get_settings


def build_user_creation_exchange() -> RabbitExchange:
    settings = get_settings()
    return RabbitExchange(settings.MQ_EXCHANGE_NAME, ExchangeType.DIRECT, durable=True)
