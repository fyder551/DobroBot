from vkbottle import GroupEventType, Keyboard, Callback, KeyboardButtonColor, OpenLink
from vkbottle.bot import MessageEvent
from app.bot_instance import bot
from app.config import CHAT_ID, GROUP_ID
from app.database.crud import get_user_by_vk_id, get_event_by_id, create_response, get_event_responses_count, get_session, get_event_responses
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

                # --- ПРОВЕРКА ПОЛА (ТОЛЬКО ЕСЛИ ПОЛ ИЗВЕСТЕН) ---
        if user.gender and user.gender != "unknown":
            if event_db.gender_required == "male" and user.gender != "male":
                await event.show_snackbar("❌ Это мероприятие только для парней!")
                return
            if event_db.gender_required == "female" and user.gender != "female":
                await event.show_snackbar("❌ Это мероприятие только для девушек!")
                return
        
        # --- ПРОВЕРКА ЛИМИТА ---
        current_count = get_event_responses_count(event_id)
        max_vol_str = str(event_db.max_volunteers).lower()
        
        if max_vol_str != "все" and current_count >= int(max_vol_str):
            await event.show_snackbar("❌ Мест больше нет!")
            return

        # Записываем в БД
        response = create_response(event_id=event_db.id, user_id=user.id)
        
        # Если пользователь уже записан (response вернул None)
        if not response:
            await event.show_snackbar("ℹ️ Ты уже записался!")
            return # Выходим, сообщение не трогаем, кнопка остается зеленой

        # Пересчитываем после записи
        count = get_event_responses_count(event_id)

        # Формируем текст
        vol_text = "👥 Нужны все!" if max_vol_str == "все" else f"👥 Нужны {event_db.max_volunteers} человек"
        chat_text = (
            f"📌 {event_db.title}\n\n"
            f"📅 Дата: {event_db.date.strftime('%d.%m')} с {event_db.start_time.strftime('%H:%M')} до {event_db.end_time.strftime('%H:%M')}\n"
            f"📍 Место: {event_db.location}\n"
            f"{vol_text}\n\n"
            f"📝 Описание:\n{event_db.description}"
        )
        if event_db.bonus_info: chat_text += f"\n\n🎁 Бонусы: {event_db.bonus_info}"
        if event_db.chat_link: chat_text += f"\n🔗 Чат: {event_db.chat_link}"

                # --- ФОРМИРУЕМ КНОПКИ ---
        counter_text = f"{count}" if max_vol_str == "все" else f"{count}/{event_db.max_volunteers}"
        app_link = f"https://vk.com/app54895625#event_id={event_db.id}"
        
        is_full = max_vol_str != "все" and count >= int(max_vol_str)
        
        if is_full:
            kb = (
                Keyboard(inline=True)
                .add(Callback("❌ Мест нет", payload={"cmd": "noop"}), color=KeyboardButtonColor.NEGATIVE)
                .add(OpenLink(app_link, label=f"👥 Список ({counter_text})"), color=KeyboardButtonColor.SECONDARY)
            )
        else:
            kb = (
                Keyboard(inline=True)
                .add(Callback("✅ Я пойду", payload={"cmd": "join_chat", "id": str(event_db.id)}), color=KeyboardButtonColor.POSITIVE)
                .add(OpenLink(app_link, label=f"👥 Список ({counter_text})"), color=KeyboardButtonColor.SECONDARY)
            )

        # Редактируем сообщение
        try:
            await bot.api.messages.edit(
                peer_id=event.peer_id,
                cmid=event.conversation_message_id,
                group_id=GROUP_ID,
                message=chat_text,
                keyboard=kb.get_json()
            )
            logger.info(f"✅ Сообщение обновлено. Записалось: {count}")
        except Exception as e:
            logger.error(f"❌ Ошибка редактирования: {e}")

        # Показываем окошко успеха (видит только нажавший)
        await event.show_snackbar(f"✅ Успешно! Всего: {count}")

    except Exception as e:
        logger.error(f"Критическая ошибка в join_chat: {e}")

# Обработчик для серой кнопки
@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "noop"})
async def noop_handler(event: MessageEvent):
    # Эта кнопка срабатывает, когда мест нет, или когда человек уже записан
    await event.show_snackbar("На это мероприятие больше нельзя записаться!")


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

@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "view_list"})
async def view_list_callback(event: MessageEvent):
    try:
        event_id = int(event.payload["id"])
        event_db = get_event_by_id(event_id) # Получаем данные ивента
        user = get_user_by_vk_id(event.user_id) # Получаем того, кто нажал
        
        # ПРОВЕРКА: Только создатель может смотреть список
        if not user or event_db.author_id != user.id:
            await event.show_snackbar("⛔ Список записавшихся доступен только создателю!")
            return

        responses = get_event_responses(event_id)
        
        if not responses:
            await event.show_snackbar("Пока никто не записался 😢")
        else:
            names = [f"{r.user.first_name} {r.user.last_name}" if r.user.last_name else r.user.first_name for r in responses if r.user]
            if not names:
                await event.show_snackbar("Пока никто не записался 😢")
                return
                
            display = ", ".join(names[:5])
            if len(names) > 5:
                display += f" и еще {len(names)-5}"
            await event.show_snackbar(f"Записались: {display}")
    except Exception as e:
        logger.error(f"Ошибка при выводе списка: {e}")
        await event.show_snackbar("❌ Ошибка при загрузке списка")