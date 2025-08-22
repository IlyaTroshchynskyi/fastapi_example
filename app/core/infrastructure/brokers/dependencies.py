from fastapi import Request
from faststream.rabbit import RabbitBroker


def get_rabbit_broker(request: Request) -> RabbitBroker:
    return request.app.state.broker
