import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from app.bot_instance import bot
from app.config import CHAT_ID

async def main():
    chat_id = CHAT_ID - 2000000000
    print(f"Спрашиваем у ВК информацию о чате {chat_id}...")
    try:
        chat_info = await bot.api.messages.get_chat(chat_id=chat_id)
        print(f"✅ Успех! Бот видит чат: {chat_info.title}")
        print(f"Участники: {[u.first_name for u in chat_info.users]}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())