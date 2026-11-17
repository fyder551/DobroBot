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
        
        # --- АВТОРЕГИСТРАЦИЯ ---
        if not user:
            try:
                users_info = await bot.api.users.get(user_ids=event.user_id)
                if users_info:
                    vk_user = users_info[0]
                    gender = "male" if vk_user.sex == 2 else ("female" if vk_user.sex == 1 else "unknown")
                    from app.database.crud import get_or_create_user
                    user = get_or_create_user(
                        vk_id=event.user_id,
                        first_name=vk_user.first_name,
                        last_name=vk_user.last_name or "",
                        gender=gender
                    )
            except Exception as e:
                logger.error(f"Ошибка авторегистрации: {e}")
                return

        event_id = int(event.payload["id"])
        event_db = get_event_by_id(event_id)
        if not event_db: return

        # Пытаемся записать в БД
        response = create_response(event_id=event_db.id, user_id=user.id)
        
        # Считаем актуальное количество записавшихся (в любом случае)
        count = get_event_responses_count(event_id)

        # Показываем окошко пользователю
        if not response:
            await event.show_snackbar(f"ℹ️ Ты уже записался! Всего: {count}")
        else:
            await event.show_snackbar(f"✅ Успешно! Всего: {count}")

        # --- ОБНОВЛЯЕМ СООБЩЕНИЕ (ДАЖЕ ЕСЛИ УЖЕ ЗАПИСАН) ---
        try:
            # Умный текст для кнопки
            if str(event_db.max_volunteers).lower() == "все":
                btn_text = f"👥 Список ({count}/все)"
            else:
                btn_text = f"👥 Список ({count}/{event_db.max_volunteers})"
            
            # Ссылка через решетку
            app_link = f"https://vk.com/app54895625#event_id={event_db.id}"
            
            kb = (
                Keyboard(inline=True)
                .add(Callback("✅ Я пойду", payload={"cmd": "join_chat", "id": str(event_db.id)}), color=KeyboardButtonColor.POSITIVE)
                .add(OpenLink(app_link, btn_text), color=KeyboardButtonColor.SECONDARY)
            )

            # ВАЖНО: вызываем edit с cmid
            await bot.api.messages.edit(
                peer_id=event.peer_id,
                cmid=event.conversation_message_id,
                group_id=GROUP_ID,
                message=chat_text, # текстовое описание мероприятия
                keyboard=kb.get_json()
            )
            logger.info(f"✅ Сообщение обновлено. Записалось: {count}")
        except Exception as e:
            logger.error(f"❌ ВК НЕ ДАЛ ОБНОВИТЬ КНОПКУ: {e}")

            # 4. Формируем текст сообщения (без дублирования счетчика)
            chat_text = (
                f"📌 {event_db.title}\n\n"
                f"📅 Дата: {event_db.date.strftime('%d.%m')} с {event_db.start_time.strftime('%H:%M')} до {event_db.end_time.strftime('%H:%M')}\n"
                f"📍 Место: {event_db.location}\n"
                f"📝 Описание:\n{event_db.description}"
            )

            # 5. Редактируем сообщение (берем ID прямо из события)
            await bot.api.messages.edit(
                peer_id=event.peer_id,
                cmid=event.conversation_message_id,
                group_id=GROUP_ID,
                message=chat_text,
                keyboard=kb.get_json()
            )
            logger.info(f"✅ Кнопка обновлена. Записалось: {count}")

        except Exception as e:
            logger.error(f"❌ ВК НЕ ДАЛ ОБНОВИТЬ КНОПКУ: {e}")

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