import sys
import os

# Добавляем корень проекта в пути поиска Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from app.bot_instance import bot
from app.config import CHAT_ID

async def main():
    print(f"Пробуем отправить в CHAT_ID: {CHAT_ID}")
    try:
        # Пробуем 1: Отправка по peer_id
        await bot.api.messages.send(
            peer_id=CHAT_ID,
            message="Тест 1: Отправка по peer_id",
            random_id=0
        )
        print("✅ Тест 1 (peer_id) прошел успешно!")
    except Exception as e:
        print(f"❌ Ошибка в Тесте 1 (peer_id): {e}")

    try:
        # Пробуем 2: Отправка по chat_id
        chat_id = CHAT_ID - 2000000000
        await bot.api.messages.send(
            chat_id=chat_id,
            message="Тест 2: Отправка по chat_id",
            random_id=0
        )
        print("✅ Тест 2 (chat_id) прошел успешно!")
    except Exception as e:
        print(f"❌ Ошибка в Тесте 2 (chat_id): {e}")

if __name__ == "__main__":
    asyncio.run(main())