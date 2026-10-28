from vkbottle import Keyboard, Text, KeyboardButtonColor, Callback, GroupEventType
from vkbottle.bot import Message, MessageEvent


from app.bot_instance import bot
from app.database.crud import (
    get_user_by_vk_id,
    update_user_full_name,
    get_approved_events,
    get_user_responses,
    get_event_by_id,
)
from app.keyboards.main_menu import get_main_menu_keyboard
from app.states import SettingsState, SearchState
from app.utils.validators import validate_full_name
from datetime import datetime
from app.database.models import Response
from app.database.crud import get_session


def get_profile_keyboard() -> str:
    """Клавиатура профиля."""
    return (
        Keyboard(one_time=False, inline=False)
        .add(Text("✏️ Изменить ФИО"), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("⬅️ В главное меню"), color=KeyboardButtonColor.SECONDARY)
        .get_json()
    )


@bot.on.message(text=["👤 Профиль", "Профиль"])
async def profile_handler(message: Message):
    """Показывает профиль пользователя."""
    user = get_user_by_vk_id(message.from_id)

    if not user or not user.full_name:
        await message.answer("Ты ещё не зарегистрирован. Напиши /start")
        return

    gender_ru = "Мужской" if user.gender == "male" else "Женский"
    role_ru = {
        "volunteer": "Волонтёр",
        "organizer": "Организатор",
        "admin": "Администратор",
    }.get(user.role, "Волонтёр")

    await message.answer(
        f"👤 Твой профиль:\n\n"
        f"📛 ФИО: {user.full_name}\n"
        f"⚧ Пол: {gender_ru}\n"
        f"🎓 Вуз: {user.university}\n"
        f"🎭 Роль: {role_ru}",
        keyboard=get_profile_keyboard(),
    )


@bot.on.message(text=["✏️ Изменить ФИО"])
async def edit_name_start(message: Message):
    """Начало изменения ФИО."""
    await bot.state_dispenser.set(message.peer_id, SettingsState.WAITING_FOR_NEW_NAME)
    await message.answer(
        "✏️ Введи новое ФИО.\n\n"
        "Порядок: Фамилия Имя Отчество\n"
        "Пример: Иванов Иван Иванович\n\n"
        "Для отмены нажми кнопку «⬅️ В главное меню»",
    )


@bot.on.message(state=SettingsState.WAITING_FOR_NEW_NAME)
async def edit_name_process(message: Message):
    """Обрабатывает новое ФИО или отмену."""

    # Если пользователь нажал любую кнопку меню или команду — отменяем ввод имени
    cancel_texts = [
        "⬅️ В главное меню",
        "⬅️ Назад",
        "/start",
        "Начать",
        "👤 Профиль",
        "Профиль",
        "⚙️ Настройки",
        "Настройки",
        "🔍 Найти мероприятие",
        "Найти мероприятие",
    ]

    if message.text in cancel_texts:
        await bot.state_dispenser.delete(message.peer_id)  # Сбрасываем состояние
        user = get_user_by_vk_id(message.from_id)
        role = user.role if user else "volunteer"
        await message.answer(
            "Действие отменено. Главное меню:",
            keyboard=get_main_menu_keyboard(role),
        )
        return

    if message.text.startswith("/"):
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer("Действие отменено.")
        return

    # Валидация ФИО
    user = get_user_by_vk_id(message.from_id)
    if not user:
        return

    text = message.text.strip()
    words = text.split()

    is_valid, error_msg = validate_full_name(text, user.gender)
    if not is_valid:
        await message.answer(f"❌ {error_msg}\n\nВведи ФИО снова.")
        return

    update_user_full_name(message.from_id, text)
    await bot.state_dispenser.delete(message.peer_id)
    short_name = words[1]
    await message.answer(
        f"✅ Готово! Теперь тебя зовут {short_name}.",
        keyboard=get_main_menu_keyboard(user.role),
    )


# --- ФУНКЦИЯ ДЛЯ ОТОБРАЖЕНИЯ КАРТОЧКИ ---
async def show_event_card(
    message_or_event, event, index: int, total: int, user, edit: bool = False
):
    """Показывает карточку (или редактирует текущую)."""

    # Красивые тексты для пола
    gender_ru = {
        "all": "👥 Любые",
        "male": "👦 Только парни",
        "female": "👧 Только девушки",
    }.get(event.gender_required, "👥 Любые")

    is_registered = False
    current_responses = 0

    if user:

        session = get_session()
        try:
            # Считаем, сколько уже записалось
            current_responses = (
                session.query(Response)
                .filter_by(event_id=event.id, status="confirmed")
                .count()
            )
            # Проверяем, записан ли текущий пользователь
            existing = (
                session.query(Response)
                .filter_by(event_id=event.id, user_id=user.id)
                .first()
            )
            if existing:
                is_registered = True
        finally:
            session.close()

    # Проверка лимита
    is_full = False
    if event.max_volunteers and event.max_volunteers.isdigit():
        if current_responses >= int(event.max_volunteers):
            is_full = True

    from app.database.crud import get_session
    from app.database.models import User

    session = get_session()
    org = session.query(User).filter_by(id=event.organizer_id).first()
    session.close()

    # Формат ссылки ВК: [id123456|Имя]. Она станет синей и кликабельной!
    org_link = f"[id{org.vk_id}|{org.full_name.split()[1]}]" if org else "Не указан"

    # Собираем текст карточки
    lines = [
        f"📌 {event.title}",
        f"📅 {event.date.strftime('%d.%m.%Y')} в {event.time.strftime('%H:%M')}",
        f"📍 {event.location}",
        f"📝 {event.description}",
        "",  # Один отступ для красоты
        f"👥 Нужно: {event.max_volunteers} чел. ({gender_ru})",
        f"📊 Записались: {current_responses} чел.",
    ]

    # Добавляем бонусы и чат ТОЛЬКО если они есть
    if event.bonus_info and event.bonus_info.lower() != "нет":
        lines.append(f"🎁 Бонусы: {event.bonus_info}")
    if event.chat_link:
        lines.append(f"🔗 Чат: {event.chat_link}")

    # Добавляем организатора и подвал
    lines.extend(
        [f"👤 Организатор: {org_link}", "", f"(Мероприятие {index + 1} из {total})"]
    )

    text = "\n".join(lines)

    kb = Keyboard(inline=True)

    if user and (user.id == event.organizer_id or user.role == "admin"):
        kb.add(
            Callback(
                f"👥 Отклики ({current_responses})",
                payload={"cmd": "view_resps", "id": str(event.id)},
            ),
            color=KeyboardButtonColor.PRIMARY,
        )
        kb.row()
    if is_registered:
        kb.add(
            Callback("✅ Вы записаны", payload={"cmd": "noop"}),
            color=KeyboardButtonColor.SECONDARY,
        )
    elif is_full:
        kb.add(
            Callback("❌ Мест нет", payload={"cmd": "noop"}),
            color=KeyboardButtonColor.NEGATIVE,
        )
    else:
        kb.add(
            Callback(
                "✅ Откликнуться",
                payload={
                    "cmd": "join",
                    "id": str(event.id),
                    "index": index,
                    "total": total,
                },
            ),
            color=KeyboardButtonColor.POSITIVE,
        )

    if index > 0:
        kb.add(
            Callback("⬅️ Назад", payload={"cmd": "prev"}),
            color=KeyboardButtonColor.SECONDARY,
        )
    if index < total - 1:
        kb.add(
            Callback("➡️ Вперед", payload={"cmd": "next"}),
            color=KeyboardButtonColor.SECONDARY,
        )

    if edit:
        try:
            await bot.api.messages.edit(
                peer_id=message_or_event.peer_id,
                cmid=message_or_event.conversation_message_id,
                message=text,
                keyboard=kb.get_json(),
            )
        except Exception:
            from app.logger import logger

            logger.exception("Ошибка редактирования сообщения")
    else:
        import random

        await message_or_event.answer(
            text, keyboard=kb.get_json(), random_id=random.randint(1, 1000000)
        )


@bot.on.message(text=["🔍 Найти мероприятие", "Найти мероприятие"])
async def search_handler(message: Message):
    await bot.state_dispenser.delete(message.peer_id)
    user = get_user_by_vk_id(message.from_id)
    role = user.role if user else "volunteer"

    events = get_approved_events()
    if not events:
        await message.answer(
            "🔍 Пока нет активных мероприятий.", keyboard=get_main_menu_keyboard(role)
        )
        return

    event_ids = [e.id for e in events]
    await bot.state_dispenser.set(
        message.peer_id, SearchState.BROWSING, event_ids=event_ids, index=0
    )

    await show_event_card(message, events[0], 0, len(events), user=user, edit=False)


@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "next"}
)
async def next_event_handler(event: MessageEvent):
    # МГНОВЕННО убираем спиннер
    await event.show_snackbar("Загрузка...")

    try:
        state = await bot.state_dispenser.get(event.peer_id)
        if not state:
            await event.show_snackbar(
                "Сессия истекла. Нажми 'Найти мероприятие' заново."
            )
            return

        event_ids = state.payload["event_ids"]
        new_index = state.payload["index"] + 1

        await bot.state_dispenser.set(
            event.peer_id, SearchState.BROWSING, event_ids=event_ids, index=new_index
        )

        event_db = get_event_by_id(event_ids[new_index])
        user = get_user_by_vk_id(event.user_id)

        await show_event_card(
            event, event_db, new_index, len(event_ids), user=user, edit=True
        )
    except Exception:
        from app.logger import logger

        logger.exception("Ошибка при нажатии 'Вперед'")
        await event.show_snackbar("❌ Ошибка при перелистывании")


@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "prev"}
)
async def prev_event_handler(event: MessageEvent):
    # МГНОВЕННО убираем спиннер
    await event.show_snackbar("Загрузка...")

    try:
        state = await bot.state_dispenser.get(event.peer_id)
        if not state:
            await event.show_snackbar(
                "Сессия истекла. Нажми 'Найти мероприятие' заново."
            )
            return

        event_ids = state.payload["event_ids"]
        new_index = state.payload["index"] - 1

        await bot.state_dispenser.set(
            event.peer_id, SearchState.BROWSING, event_ids=event_ids, index=new_index
        )

        event_db = get_event_by_id(event_ids[new_index])
        user = get_user_by_vk_id(event.user_id)

        await show_event_card(
            event, event_db, new_index, len(event_ids), user=user, edit=True
        )
    except Exception:
        from app.logger import logger

        logger.exception("Ошибка при нажатии 'Назад'")
        await event.show_snackbar("❌ Ошибка при перелистывании")


# Обработчик для серой кнопки
@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "noop"}
)
async def noop_handler(event: MessageEvent):
    await event.show_snackbar("Вы уже записаны на это мероприятие!")


# --- МОИ ОТКЛИКИ ---
@bot.on.message(text=["📝 Мои отклики", "Мои отклики"])
async def my_responses_handler(message: Message):
    await bot.state_dispenser.delete(message.peer_id)
    user = get_user_by_vk_id(message.from_id)
    if not user:
        return

    responses = get_user_responses(user.id)
    if not responses:
        await message.answer(
            "У тебя пока нет откликов на мероприятия.",
            keyboard=get_main_menu_keyboard(user.role),
        )
        return

    text = "📝 Твои отклики:\n\n"
    today = datetime.now().date()

    for r in responses:
        # Определяем статус мероприятия
        if r.event.date >= today:
            date_status = "🟢 Активно"
        else:
            date_status = "⚪ Завершено"

        # Определяем статус присутствия (отметил ли организатор)
        if r.attended:
            attendance_status = "✅ Вы пришли"
        elif r.event.date < today:
            attendance_status = "❌ Вы не пришли"
        else:
            attendance_status = "🕒 Ожидается"

        text += (
            f"📌 {r.event.title} ({date_status})\n"
            f"📅 {r.event.date.strftime('%d.%m.%Y')} в {r.event.time.strftime('%H:%M')}\n"
            f"Ваш статус: {attendance_status}\n"
            f"───────────────\n"
        )

    text += f"\nВсего: {len(responses)} шт."
    await message.answer(text, keyboard=get_main_menu_keyboard(user.role))


# --- ВОЗВРАТ В МЕНЮ ---
@bot.on.message(text=["⬅️ В главное меню", "⬅️ Назад"])
async def back_to_menu(message: Message):
    await bot.state_dispenser.delete(message.peer_id)
    user = get_user_by_vk_id(message.from_id)
    if not user:
        return
    await message.answer(
        "Главное меню:",
        keyboard=get_main_menu_keyboard(user.role),
    )
