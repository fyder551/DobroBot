import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.bot_instance import bot
from app.database.db import init_db
from app.logger import logger  # <-- Импортируем логгер

from app.handlers import start  # noqa: F401
from app.handlers import create # noqa: F401
from app.handlers import responses # noqa: F401


# Перехватываем ВСЕ критические ошибки Python и пишем в лог
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("КРИТИЧЕСКАЯ ОШИБКА:", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception


if __name__ == "__main__":
    logger.info("🛠️ Инициализация БД...")
    init_db()
    logger.info("🤖 Добробот v2.0 запускается...")
    bot.run()