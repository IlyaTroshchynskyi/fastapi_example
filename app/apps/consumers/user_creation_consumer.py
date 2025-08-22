import asyncio
import logging
import random
import time

from aio_pika import IncomingMessage
from faststream.rabbit.fastapi import RabbitBroker, RabbitMessage, RabbitRouter

from app.apps.consumers.exchanges import get_user_creation_exchange
from app.apps.consumers.queues import dlq_q_test, q_test
from app.apps.consumers.schemas import UserCreationMsg
from app.core.config import get_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


router = RabbitRouter(get_settings().MQ_URL)


@router.subscriber(q_test, get_user_creation_exchange())
async def handle_user_creation_msg(body: UserCreationMsg, msg: RabbitMessage):
    raw: IncomingMessage = msg.raw_message
    logger.info('[EMAIL] Received message: %r (delivery_tag=%s)', body, raw.delivery_tag)

    start_time = time.time()
    await asyncio.sleep(random.uniform(0.1, 1.0))
    should_fail = random.random() < 0.5

    if should_fail:
        logger.error('Failed to process %r, pushing to DLQ', body)
        await msg.reject(requeue=False)
        return

    end_time = time.time()
    logger.info('Processed in %.2fs - acking %r', end_time - start_time, body)
    await msg.ack()


@router.after_startup
async def setup_infrastructure(_):
    await declare_queue(router.broker)


async def declare_queue(broker: RabbitBroker):
    await broker.declare_exchange(get_user_creation_exchange())
    await broker.declare_queue(q_test)
    await broker.declare_queue(dlq_q_test)
