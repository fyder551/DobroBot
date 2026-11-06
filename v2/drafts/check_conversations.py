import sys
import os

# Добавляем корень v2 в пути поиска
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from app.bot_instance import bot
from app.config import GROUP_ID

async def main():
    print(f"🔍 Запрашиваем список бесед для сообщества ID: {GROUP_ID}...")
    try:
        # Запрашиваем беседы (extended=1 чтобы получить названия)
        response = await bot.api.messages.get_conversations(
            group_id=GROUP_ID,
            count=200,
            extended=1
        )
        
        conversations = response.items
        print(f"\n✅ Найдено бесед: {len(conversations)}\n")
        
        for conv in conversations:
            peer_id = conv.conversation.peer.id
            chat_id = conv.conversation.peer.local_id if hasattr(conv.conversation.peer, 'local_id') else None
            # Пытаемся найти название в profiles/groups
            title = "Без названия"
            if conv.conversation.chat_settings:
                title = conv.conversation.chat_settings.title
            
            print(f"📌 Название: {title}")
            print(f"   peer_id: {peer_id}")
            print(f"   chat_id: {chat_id}")
            print(f"   последнее сообщение: {conv.last_message.text[:50] if conv.last_message else 'Нет'}")
            print("-" * 40)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())