import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.bot_instance import bot
from vkbottle.bot import Message

# Ловим ВСЕ сообщения (и в ЛС, и в чатах)
@bot.on.message()
async def catch_all(message: Message):
    print(f"📥 ПОЙМАНО СООБЩЕНИЕ! peer_id: {message.peer_id}, from_id: {message.from_id}, text: {message.text}")
    # Если это из чата (peer_id начинается на 2000...)
    if message.peer_id >= 2000000000:
        print(f"✅ ЭТО СООБЩЕНИЕ ИЗ ЧАТА! Итоговый chat_id для отправки: {message.peer_id}")

if __name__ == "__main__":
    print("🤖 Бот слушает ВСЕ сообщения (включая чаты). Напиши что-нибудь в чат!")
    bot.run()