import truststore
import sys
from app.logger import logger

# Эта команда должна быть выполнена ДО импорта других библиотек
truststore.inject_into_ssl()

from app.bot_instance import bot  # noqa: E402
from app.database.db import init_db  # noqa: E402

from app.handlers import start  # noqa: E402, F401
from app.handlers import menu  # noqa: E402, F401
from app.handlers import settings  # noqa: E402, F401
from app.handlers import create  # noqa: E402, F401
from app.handlers import admin  # noqa: E402, F401
from app.handlers import responses  # noqa: E402, F401
from app.handlers import my_events  # noqa: E402, F401


# Перехватываем критические ошибки Python
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("КРИТИЧЕСКАЯ ОШИБКА:", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception


if __name__ == "__main__":
    print("🛠️  Инициализация БД...")
    init_db()

    print("🤖 Бот запускается...")
    bot.run()
