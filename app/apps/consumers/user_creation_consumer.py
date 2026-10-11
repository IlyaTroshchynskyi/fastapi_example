import asyncio
import logging
import random
import time

from aio_pika import IncomingMessage
from faststream.rabbit.fastapi import RabbitBroker, RabbitMessage, RabbitRouter

from app.apps.consumers.exchanges import build_user_creation_exchange
from app.apps.consumers.queues import user_creation_dead_letter_queue, user_creation_queue
from app.apps.consumers.schemas import UserCreationMessage
from app.core.config import get_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


router = RabbitRouter(get_settings().MQ_URL)


@router.subscriber(user_creation_queue, build_user_creation_exchange())
async def consume_user_creation_message(
    user_creation_message: UserCreationMessage, rabbit_message: RabbitMessage
) -> None:
    raw_message: IncomingMessage = rabbit_message.raw_message
    logger.info('[EMAIL] Received message: %r (delivery_tag=%s)', user_creation_message, raw_message.delivery_tag)

    start_time = time.time()
    await asyncio.sleep(random.uniform(0.1, 1.0))
    should_fail = random.random() < 0.5

    if should_fail:
        logger.error('Failed to process %r, pushing to DLQ', user_creation_message)
        await rabbit_message.reject(requeue=False)
        return

    end_time = time.time()
    logger.info('Processed in %.2fs - acking %r', end_time - start_time, user_creation_message)
    await rabbit_message.ack()


@router.after_startup
async def setup_infrastructure(_: RabbitBroker) -> None:
    await declare_user_creation_topology(router.broker)


async def declare_user_creation_topology(broker: RabbitBroker) -> None:
    await broker.declare_exchange(build_user_creation_exchange())
    await broker.declare_queue(user_creation_queue)
    await broker.declare_queue(user_creation_dead_letter_queue)
