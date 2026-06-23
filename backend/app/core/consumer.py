"""RabbitMQ consumer — запускается отдельным процессом.

    cd backend && python -m app.core.consumer
"""
import logging
import sys

sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("consumer")


def handle_order(data: dict):
    """Обработка заказа из очереди."""
    logger.info("Обработка заказа #%s на сумму %s ₽", data.get("order_id"), data.get("total"))


def handle_notification(data: dict):
    """Обработка уведомления."""
    logger.info("Уведомление: %s", data.get("message", ""))


def main():
    from app.core.rabbitmq import consume

    queues = {
        "orders": handle_order,
        "notifications": handle_notification,
    }

    queue = sys.argv[1] if len(sys.argv) > 1 else "orders"
    if queue not in queues:
        print(f"Очереди: {', '.join(queues.keys())}")
        sys.exit(1)

    logger.info("Запуск consumer для очереди: %s", queue)
    consume(queue, queues[queue])


if __name__ == "__main__":
    main()
