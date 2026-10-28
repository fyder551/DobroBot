from vkbottle import GroupEventType
from vkbottle.bot import MessageEvent

from app.bot_instance import bot
from app.database.crud import get_user_by_vk_id, get_event_by_id, create_response
from app.handlers.menu import show_event_card
from app.database.crud import get_event_responses

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
