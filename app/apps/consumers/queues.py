from faststream.rabbit import RabbitQueue
from faststream.rabbit.schemas.queue import ClassicQueueArgs

from app.core.config import get_settings

args: ClassicQueueArgs = {'x-dead-letter-exchange': '', 'x-dead-letter-routing-key': get_settings().MQ_DLQ_NAME}

q_test = RabbitQueue(
    get_settings().MQ_QUEUE_NAME,
    durable=True,
    arguments=args,
)

dlq_q_test = RabbitQueue(get_settings().MQ_DLQ_NAME, durable=True)
