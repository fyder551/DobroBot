import logging
import sys
import os

# Создаем папку logs, если её нет
if not os.path.exists('logs'):
    os.makedirs('logs')

formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

# Логгер для записи в файл (теперь в папке logs)
file_handler = logging.FileHandler('logs/bot_errors.log', encoding='utf-8')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(formatter)

# Логгер для вывода в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

logger = logging.getLogger("DobroBot")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)