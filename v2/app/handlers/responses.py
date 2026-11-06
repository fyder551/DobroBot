from vkbottle import GroupEventType, Keyboard, Callback, KeyboardButtonColor
from vkbottle.bot import MessageEvent
from app.bot_instance import bot
from app.config import CHAT_ID, GROUP_ID
from app.database.crud import get_user_by_vk_id, get_event_by_id, create_response, get_event_responses_count, get_session
from app.logger import logger
from app.database.models import Event
import re
from vkbottle.bot import Message


@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "join_chat"})
async def join_chat_callback(event: MessageEvent):
    try:
        user = get_user_by_vk_id(event.user_id)
        if not user:
            return

        event_id = int(event.payload["id"])
        event_db = get_event_by_id(event_id)
        if not event_db: return

        # Пытаемся записать в БД
        response = create_response(event_id=event_db.id, user_id=user.id)
        if not response:
            await event.show_snackbar("ℹ️ Ты уже записался!")
            return

        count = get_event_responses_count(event_id)

        # Формируем текст
        vol_text = "👥 Нужны все!" if str(event_db.max_volunteers).lower() == "все" else f"👥 Нужны {event_db.max_volunteers} человек"
        chat_text = (
            f"📌 {event_db.title}\n\n"
            f"📅 Дата: {event_db.date.strftime('%d.%m')} с {event_db.start_time.strftime('%H:%M')} до {event_db.end_time.strftime('%H:%M')}\n"
            f"📍 Место: {event_db.location}\n"
            f"{vol_text}\n\n"
            f"📝 Описание:\n{event_db.description}"
        )
        if event_db.bonus_info: chat_text += f"\n\n🎁 Бонусы: {event_db.bonus_info}"
        if event_db.chat_link: chat_text += f"\n🔗 Чат: {event_db.chat_link}"
        chat_text += f"\n\n📊 Записались: {count} / {event_db.max_volunteers}"

        # ОДНА СЕРАЯ КНОПКА
        kb = (
            Keyboard(inline=True)
            .add(Callback("✅ Вы записаны", payload={"cmd": "noop"}), color=KeyboardButtonColor.SECONDARY)
        )

        # --- МАГИЯ: РЕДАКТИРУЕМ СООБЩЕНИЕ, ИСПОЛЬЗУЯ ID ИЗ СОБЫТИЯ ---
        try:
            await bot.api.messages.edit(
                peer_id=event.peer_id,               # Берем из клика
                cmid=event.conversation_message_id,  # Берем из клика!
                group_id=GROUP_ID,
                message=chat_text,
                keyboard=kb.get_json()
            )
            logger.info(f"✅ Сообщение обновлено!")
        except Exception as e:
            logger.error(f"❌ Ошибка редактирования: {e}")

        # Показываем окошко успеха в конце
        await event.show_snackbar(f"✅ Успешно! Всего: {count}")

    except Exception as e:
        logger.error(f"Критическая ошибка в join_chat: {e}")
# Обработчик для серой кнопки
@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "noop"})
async def noop_handler(event: MessageEvent):
    await event.show_snackbar("Вы уже записаны!")


@bot.on.message()
async def catch_own_messages(message: Message):
    # Ловим только сообщения от нашего бота в нашем чате
    if message.peer_id == CHAT_ID and message.from_id == -GROUP_ID:
        # Ищем наш скрытый маркер [ID:1]
        match = re.search(r"\[ID:(\d+)\]", message.text)
        if match:
            event_id = int(match.group(1))
            from app.database.crud import get_session
            from app.database.models import Event
            
            session = get_session()
            try:
                ev = session.query(Event).filter_by(id=event_id).first()
                if ev and not ev.vk_post_id:
                    ev.vk_post_id = message.id
                    ev.vk_post_cmid = message.conversation_message_id
                    session.commit()
                    print(f"✅ ПОЙМАЛИ ID ИЗ СОБЫТИЯ: message_id={message.id}, cmid={message.conversation_message_id}")
            finally:
                session.close()


# Этот обработчик ловит сообщения от самого бота в чате
@bot.on.message()
async def catch_bot_messages(message: Message):
    # Проверяем, что это наше сообщество и наш чат
    if message.peer_id == CHAT_ID and message.from_id == -GROUP_ID:
        # Если у сообщения есть random_id
        if message.random_id:
            session = get_session()
            try:
                # Ищем мероприятие по random_id
                ev = session.query(Event).filter_by(vk_post_random_id=message.random_id).first()
                if ev and not ev.vk_post_id:
                    ev.vk_post_id = message.id
                    ev.vk_post_cmid = message.conversation_message_id
                    session.commit()
                    print(f"✅ ПЕРЕХВАТИЛИ ID! message_id={message.id}, cmid={message.conversation_message_id}")
            finally:
                session.close()