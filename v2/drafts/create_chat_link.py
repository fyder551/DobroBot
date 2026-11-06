import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from app.bot_instance import bot

async def main():
    print("🤖 Бот создает новый чат и генерирует ссылку...")
    MY_VK_ID = 455965497 
    
    try:
        # 1. Создаем чат (без добавления людей, чтобы не было ошибок)
        response = await bot.api.messages.create_chat(
            title="Волонтеры ВГУИТ (Рабочий чат)"
        )
        chat_id = response.chat_id
        peer_id = 2000000000 + chat_id
        print(f"✅ Чат создан! chat_id: {chat_id}, peer_id: {peer_id}")

        # 2. Получаем ссылку-приглашение для этого чата
        invite_link = await bot.api.messages.get_invite_link(
            peer_id=peer_id
        )
        print(f"\n🔗 ВОТ ССЫЛКА ДЛЯ ВХОДА В ЧАТ:\n{invite_link}\n")
        
        # 3. Отправляем ссылку тебе в ЛС от лица бота
        await bot.api.messages.send(
            user_id=MY_VK_ID,
            message=f"Я создал новый рабочий чат! Переходи по ссылке, чтобы стать его участником:\n{invite_link}",
            random_id=0
        )
        print("✅ Ссылка также отправлена тебе в личные сообщения от бота!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())