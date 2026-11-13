import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# Создаем папку logs, если её нет
os.makedirs("logs", exist_ok=True)

formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')

# Файл для всех логов (максимум 5 МБ, храним 3 копии)
file_handler = RotatingFileHandler(
    'logs/bot.log', maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
)
file_handler.setFormatter(formatter)

# Вывод в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# Наш основной логгер
logger = logging.getLogger("DobroBot")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Логгер для vkbottle (чтобы видеть ошибки самого ВК)
vk_logger = logging.getLogger("vkbottle")
vk_logger.setLevel(logging.WARNING)
vk_logger.addHandler(file_handler)
vk_logger.addHandler(console_handler)