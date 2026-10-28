import logging
import sys


def setup_logger():
    """Настройка логгера для записи ошибок в файл."""
    logger = logging.getLogger("DobroBot")
    logger.setLevel(logging.DEBUG)

    # 1. Обработчик для записи в файл (сохраняем только ОШИБКИ, чтобы файл не разрастался)
    file_handler = logging.FileHandler("bot_errors.log", encoding="utf-8")
    file_handler.setLevel(logging.ERROR)

    # 2. Обработчик для вывода в консоль (как обычно)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Формат записи: [Дата Время] - Тип ошибки - Текст
    formatter = logging.Formatter(
        "[%(asctime)s] - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Создаем глобальный логгер, который будем импортировать в другие файлы
logger = setup_logger()
