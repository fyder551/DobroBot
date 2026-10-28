import re
from vkbottle import Keyboard, Text, KeyboardButtonColor
from vkbottle.bot import Message

from app.bot_instance import bot
from app.database.crud import (
    get_user_by_vk_id,
    get_event_by_id,
    approve_event,
    reject_event,
    get_session,
)
from app.database.models import User, Event
from app.keyboards.main_menu import get_main_menu_keyboard


def is_admin(vk_id: int) -> bool:
    user = get_user_by_vk_id(vk_id)
    return user is not None and user.role == "admin"


async def notify_organizer(event, approved: bool):
    session = get_session()
    try:
        organizer = session.query(User).filter_by(id=event.organizer_id).first()
    finally:
        session.close()

    if not organizer:
        return

    if organizer.role == "admin":
        return

    if approved:
        msg = f"✅ Твоё мероприятие «{event.title}» одобрено!\nОно появится в поиске для волонтёров."
    else:
        reason = event.rejection_reason or "без указания причины"
        msg = f"❌ Твоё мероприятие «{event.title}» отклонено.\nПричина: {reason}"

    try:
        await bot.api.messages.send(user_id=organizer.vk_id, message=msg, random_id=0)
    except Exception as e:
        print(f"⚠️ Не удалось уведомить организатора: {e}")


# --- НОВАЯ АДМИН-ПАНЕЛЬ ---


@bot.on.message(text=["🔔 Модерация", "Модерация"])
async def moderation_menu(message: Message):
    """Открывает список заявок на модерацию."""
    if not is_admin(message.from_id):
        await message.answer("❌ Доступ только для администраторов.")
        return

    session = get_session()
    try:
        # Ищем самое старое необработанное мероприятие
        pending_event = (
            session.query(Event)
            .filter_by(status="pending")
            .order_by(Event.created_at)
            .first()
        )
    finally:
        session.close()

    if not pending_event:
        await message.answer(
            "🎉 Отлично! Нет новых заявок на модерацию.",
            keyboard=get_main_menu_keyboard("admin"),
        )
        return

    # Создаем клавиатуру с ID мероприятия
    kb = (
        Keyboard(one_time=False, inline=False)
        .add(
            Text(f"✅ Одобрить #{pending_event.id}"), color=KeyboardButtonColor.POSITIVE
        )
        .add(
            Text(f"❌ Отклонить #{pending_event.id}"),
            color=KeyboardButtonColor.NEGATIVE,
        )
        .row()
        .add(Text("⬅️ В главное меню"), color=KeyboardButtonColor.SECONDARY)
        .get_json()
    )

    await message.answer(
        f"📋 Заявка на модерацию:\n\n"
        f"📌 Название: {pending_event.title}\n"
        f"📅 Дата: {pending_event.date.strftime('%d.%m.%Y')} в {pending_event.time.strftime('%H:%M')}\n"
        f"📍 Место: {pending_event.location}\n"
        f"📝 Описание: {pending_event.description}\n"
        f"📞 Контакты: {pending_event.contacts}\n\n"
        f"Что делаем?",
        keyboard=kb,
    )


@bot.on.message(regex=r"^✅ Одобрить #(\d+)$")
async def approve_handler(message: Message):
    """Одобряет мероприятие по кнопке."""
    if not is_admin(message.from_id):
        return

    event_id = int(re.search(r"(\d+)", message.text).group(1))
    event = get_event_by_id(event_id)

    if event and event.status == "pending":
        approve_event(event_id)
        await message.answer(f"✅ Мероприятие «{event.title}» одобрено!")
        await notify_organizer(event, approved=True)
        # Сразу показываем следующую заявку, если есть
        await moderation_menu(message)
    else:
        await message.answer("Мероприятие уже обработано или не найдено.")


@bot.on.message(regex=r"^❌ Отклонить #(\d+)$")
async def reject_handler(message: Message):
    """Отклоняет мероприятие по кнопке (без причины)."""
    if not is_admin(message.from_id):
        return

    event_id = int(re.search(r"(\d+)", message.text).group(1))
    event = get_event_by_id(event_id)

    if event and event.status == "pending":
        reject_event(event_id, reason="Не указана")
        await message.answer(f"✅ Мероприятие «{event.title}» отклонено.")
        await notify_organizer(event, approved=False)
        # Сразу показываем следующую заявку
        await moderation_menu(message)
    else:
        await message.answer("Мероприятие уже обработано или не найдено.")


# Кнопка назад из админки
@bot.on.message(text=["⬅️ В главное меню"])
async def back_to_menu_admin(message: Message):
    user = get_user_by_vk_id(message.from_id)
    if user:
        await message.answer(
            "Главное меню:", keyboard=get_main_menu_keyboard(user.role)
        )
