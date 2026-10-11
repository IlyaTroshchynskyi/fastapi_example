from faststream.rabbit import RabbitQueue
from faststream.rabbit.schemas.queue import ClassicQueueArgs

from app.core.config import get_settings

user_creation_queue_arguments: ClassicQueueArgs = {
    'x-max-length': 1000,
    'x-dead-letter-exchange': '',
    'x-dead-letter-routing-key': get_settings().MQ_DLQ_NAME,
}

user_creation_queue = RabbitQueue(
    get_settings().MQ_QUEUE_NAME,
    durable=True,
    arguments=user_creation_queue_arguments,
)

user_creation_dead_letter_queue = RabbitQueue(get_settings().MQ_DLQ_NAME, durable=True)
