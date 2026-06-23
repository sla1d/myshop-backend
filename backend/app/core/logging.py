import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logging(log_dir: str = "logs", log_level: str = "INFO"):
    """Настройка логирования с ротацией файлов."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)

    # File — ротация 10MB, 5 файлов
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    # Error file — только ошибки
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / "error.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(fmt)

    # Root logger
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)
    root.addHandler(error_handler)

    # Приглушаем шумные логгеры
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("pika").setLevel(logging.WARNING)

    return logging.getLogger("myshop")
