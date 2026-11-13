import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from app.bot_instance import bot

async def main():
    print("🤖 Бот создает новый чат...")
    
    # ВАЖНО: Твой VK ID (Фёдора)
    MY_VK_ID = 455965497 
    
    try:
        # Бот создает чат и сразу добавляет туда тебя
        response = await bot.api.messages.create_chat(
            title="Волонтеры ВГУИТ (Официальный)",
            user_ids=[MY_VK_ID]
        )
        
        # ВК возвращает ID созданного чата (например, 2 или 3)
        chat_id = response.chat_id
        peer_id = 2000000000 + chat_id
        
        print(f"✅ Чат успешно создан!")
        print(f"ID чата (chat_id): {chat_id}")
        print(f"Peer ID для отправки: {peer_id}")
        
        # Сразу пробуем отправить туда сообщение
        await bot.api.messages.send(
            peer_id=peer_id,
            message="Привет! Я создал этот чат и теперь точно могу здесь писать!",
            random_id=0
        )
        print("✅ Тестовое сообщение успешно отправлено в новый чат!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())