from vkbottle import GroupEventType, Keyboard, Callback, KeyboardButtonColor
from vkbottle.bot import MessageEvent

from app.bot_instance import bot
from app.database.crud import get_user_by_vk_id, get_event_by_id, create_response, get_session, get_event_responses
from app.handlers.menu import show_event_card
from app.database.models import Event, Response
from app.config import CHAT_ID

from app.logger import logger


@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "join"}
)
async def join_event_callback(event: MessageEvent):
    try:
        user = get_user_by_vk_id(event.user_id)
        if not user:
            await event.show_snackbar("❌ Сначала напиши /start")
            return

        event_id = int(event.payload["id"])
        index = int(event.payload.get("index", 0))
        total = int(event.payload.get("total", 1))

        event_db = get_event_by_id(event_id)

        if not event_db:
            await event.show_snackbar("❌ Мероприятие не найдено.")
            return

        # ПРОВЕРКА ЛИМИТА

        current_responses = len(get_event_responses(event_id))  # Берем текущее кол-во
        if event_db.max_volunteers and event_db.max_volunteers.isdigit():
            if current_responses >= int(event_db.max_volunteers):
                await event.show_snackbar("❌ Мест больше нет!")
                return

        # Проверка пола
        if event_db.gender_required == "male" and user.gender != "male":
            await event.show_snackbar("❌ Только для парней!")
            return
        if event_db.gender_required == "female" and user.gender != "female":
            await event.show_snackbar("❌ Только для девушек!")
            return

        response = create_response(event_id=event_db.id, user_id=user.id)

        if not response:
            await event.show_snackbar("ℹ️ Ты уже записался!")
            return

        await event.show_snackbar("✅ Успешно записался!")

        # Вызываем функцию обновления карточки
        await show_event_card(event, event_db, index, total, user, edit=True)

    except Exception:
        logger.exception("Ошибка при обработке отклика")
        await event.show_snackbar("❌ Ошибка на сервере")

@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "join_chat"})
async def join_chat_callback(event: MessageEvent):
    """Обработка кнопки 'Я пойду' прямо из чата."""
    user = get_user_by_vk_id(event.user_id)
    if not user:
        # Если человек не зареган в боте, отправляем его в ЛС
        await event.show_snackbar("❌ Сначала напиши /start в личные сообщения бота!")
        return

    event_id = int(event.payload["id"])
    event_db = get_event_by_id(event_id)

    if not event_db:
        await event.show_snackbar("❌ Мероприятие не найдено.")
        return

    # Записываем в БД
    response = create_response(event_id=event_db.id, user_id=user.id)

    if not response:
        await event.show_snackbar("ℹ️ Ты уже записался на это мероприятие!")
        return

    await event.show_snackbar("✅ Ты успешно записался!")

    # Обработчик кнопки "Я пойду"
@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "join_chat"})
async def join_chat_callback(event: MessageEvent):
    user = get_user_by_vk_id(event.user_id)
    if not user:
        await event.show_snackbar("❌ Сначала напиши /start в личные сообщения бота!")
        return

    event_id = int(event.payload["id"])
    event_db = get_event_by_id(event_id)
    if not event_db: return

    # Записываем в БД
    response = create_response(event_id=event_db.id, user_id=user.id)
    if not response:
        await event.show_snackbar("ℹ️ Ты уже записался!")
        return

    await event.show_snackbar("✅ Ты успешно записался!")

    # ОБНОВЛЯЕМ СЧЕТЧИК В ЧАТЕ
    session = get_session()
    try:
        count = session.query(Response).filter_by(event_id=event_id, status="confirmed").count()
        
        kb_chat = (
            Keyboard(inline=True)
            .add(Callback("✅ Я пойду", payload={"cmd": "join_chat", "id": str(event_id)}), color=KeyboardButtonColor.POSITIVE)
            .add(Callback(f"👥 {count}/{event_db.max_volunteers}", payload={"cmd": "view_list", "id": str(event_id)}), color=KeyboardButtonColor.SECONDARY)
        )
        
        if event_db.vk_post_cmid:
            await bot.api.messages.edit(
                chat_id=CHAT_ID - 2000000000,
                message_id=event_db.vk_post_cmid,
                keyboard=kb_chat.get_json()
            )
    finally:
        session.close()

# Обработчик кнопки "Счетчик" (показывает список)
@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "view_list"})
async def view_list_callback(event: MessageEvent):
    event_id = int(event.payload["id"])
    session = get_session()
    try:
        responses = session.query(Response).filter_by(event_id=event_id, status="confirmed").all()
        names = [r.user.full_name.split()[0] for r in responses if r.user]
    finally:
        session.close()

    if not names:
        await event.show_snackbar("Пока никто не записался 😢")
    else:
        display_names = ", ".join(names[:5])
        if len(names) > 5:
            display_names += f" и еще {len(names) - 5}..."
        await event.show_snackbar(f"Записались: {display_names}")