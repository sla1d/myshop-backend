import json
import logging
from typing import Any, Callable

from app.core.config import settings

logger = logging.getLogger(__name__)

_connection = None
_channel = None

EXCHANGE = "myshop"
QUEUES = {
    "orders": {"routing_key": "order.created", "durable": True},
    "notifications": {"routing_key": "notification.*", "durable": True},
    "reports": {"routing_key": "report.*", "durable": True},
}


def get_connection():
    """Получить синхронное соединение с RabbitMQ."""
    global _connection
    if _connection and _connection.is_open:
        return _connection
    try:
        import pika
        params = pika.URLParameters(settings.RABBITMQ_URL)
        _connection = pika.BlockingConnection(params)
        logger.info("RabbitMQ подключён: %s", settings.RABBITMQ_URL)
        return _connection
    except Exception:
        logger.warning("RabbitMQ недоступен (%s)", settings.RABBITMQ_URL)
        return None


def get_channel():
    """Получить канал с exchange/queues."""
    global _channel
    if _channel and _channel.is_open:
        return _channel
    conn = get_connection()
    if not conn:
        return None
    try:
        _channel = conn.channel()
        _channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
        for name, cfg in QUEUES.items():
            _channel.queue_declare(queue=name, durable=True)
            _channel.queue_bind(queue=name, exchange=EXCHANGE, routing_key=cfg["routing_key"])
        return _channel
    except Exception:
        return None


def publish(routing_key: str, message: dict[str, Any]) -> bool:
    """Опубликовать сообщение в RabbitMQ."""
    ch = get_channel()
    if not ch:
        return False
    try:
        ch.basic_publish(
            exchange=EXCHANGE,
            routing_key=routing_key,
            body=json.dumps(message, ensure_ascii=False, default=str),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        logger.info("📤 [%s] %s", routing_key, message)
        return True
    except Exception as e:
        logger.warning("Ошибка публикации: %s", e)
        return False


def consume(queue_name: str, callback: Callable) -> None:
    """Слушать очередь (блокирующий вызов, для отдельного процесса)."""
    ch = get_channel()
    if not ch:
        logger.warning("RabbitMQ недоступен, consumer не запущен")
        return
    try:
        def _on_message(ch, method, properties, body):
            data = json.loads(body)
            logger.info("📥 [%s] %s", method.routing_key, data)
            try:
                callback(data)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        ch.basic_qos(prefetch_count=1)
        ch.basic_consume(queue=queue_name, on_message_callback=_on_message)
        logger.info("Слушаю очередь: %s", queue_name)
        ch.start_consuming()
    except Exception as e:
        logger.warning("Consumer ошибка: %s", e)


def close():
    """Закрыть соединение."""
    global _connection, _channel
    _channel = None
    if _connection and _connection.is_open:
        try:
            _connection.close()
        except Exception:
            pass
    _connection = None
