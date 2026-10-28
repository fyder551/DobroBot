import re
from vkbottle import Keyboard, KeyboardButtonColor, Callback, GroupEventType
from vkbottle.bot import Message, MessageEvent

from app.bot_instance import bot
from app.database.crud import (
    get_organizer_events,
    get_event_responses_with_details,
    get_user_by_vk_id,
    get_session,
)
from app.database.models import Response
from app.keyboards.main_menu import get_main_menu_keyboard


# --- ГЛАВНОЕ МЕНЮ ОРГАНИЗАТОРА ---
@bot.on.message(text=["📊 Мои мероприятия"])
async def my_events_handler(message: Message):
    await bot.state_dispenser.delete(message.peer_id)  # Сбрасываем состояния
    user = get_user_by_vk_id(message.from_id)
    if not user or user.role not in ("organizer", "admin"):
        await message.answer(
            "❌ Доступно только организаторам и админам.",
            keyboard=get_main_menu_keyboard("volunteer"),
        )
        return

    events = get_organizer_events(user.id)
    if not events:
        await message.answer(
            "У тебя пока нет созданных мероприятий.",
            keyboard=get_main_menu_keyboard(user.role),
        )
        return

    text = "📊 Твои мероприятия:\nНажми на кнопку, чтобы посмотреть откликнувшихся:\n\n"

    # Создаем Inline-клавиатуру
    kb = Keyboard(inline=True)

    for e in events:
        status_emoji = (
            "🟢"
            if e.status == "approved"
            else ("🟡" if e.status == "pending" else "🔴")
        )
        # Обрезаем длинные названия
        short_title = e.title[:20] + "..." if len(e.title) > 20 else e.title
        kb.add(
            Callback(
                f"{status_emoji} {short_title} (ID {e.id})",
                payload={"cmd": "show_att", "event_id": str(e.id)},
            ),
            color=KeyboardButtonColor.SECONDARY,
        )
        kb.row()

    await message.answer(text, keyboard=kb.get_json())


# --- ГЕНЕРАЦИЯ СПИСКА С ПАГИНАЦИЕЙ (ПО 6 ЧЕЛОВЕК) ---
def generate_attendance_keyboard(event_id: int, page: int = 0):
    responses = get_event_responses_with_details(event_id)

    if not responses:
        return (
            Keyboard(inline=True)
            .add(
                Callback("Нет откликов", payload={"cmd": "noop"}),
                color=KeyboardButtonColor.SECONDARY,
            )
            .add(
                Callback("⬅️ К мероприятиям", payload={"cmd": "back_to_events"}),
                color=KeyboardButtonColor.PRIMARY,
            )
            .get_json()
        )

    items_per_page = 6
    total_pages = (len(responses) + items_per_page - 1) // items_per_page

    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_responses = responses[start_idx:end_idx]

    kb = Keyboard(inline=True)
    for i, r in enumerate(page_responses):
        if not r.user or not r.user.full_name:
            name_short = "Неизвестный"
        else:
            parts = r.user.full_name.split()
            name_short = (
                f"{parts[0]} {parts[1][0]}." if len(parts) >= 2 else r.user.full_name
            )

        if r.attended:
            kb.add(
                Callback(
                    f"✅ {name_short}",
                    payload={
                        "cmd": "toggle_att",
                        "id": str(r.id),
                        "page": str(page),
                        "event_id": str(event_id),
                    },
                ),
                color=KeyboardButtonColor.POSITIVE,
            )
        else:
            kb.add(
                Callback(
                    f"❌ {name_short}",
                    payload={
                        "cmd": "toggle_att",
                        "id": str(r.id),
                        "page": str(page),
                        "event_id": str(event_id),
                    },
                ),
                color=KeyboardButtonColor.NEGATIVE,
            )

        # ВК сам перенесет кнопки, если мы просто добавим их.
        # Но чтобы было по 2 в ряд, делаем row() после каждой второй.
        if (i + 1) % 2 == 0:
            kb.row()

    # УДАЛИЛИ БЛОК С ПУСТОЙ КНОПКОЙ. ВК сам растянет одну последнюю кнопку.

    if page > 0:
        kb.add(
            Callback(
                "⬅️ Назад",
                payload={
                    "cmd": "att_page",
                    "event_id": str(event_id),
                    "page": str(page - 1),
                },
            ),
            color=KeyboardButtonColor.PRIMARY,
        )
    if page < total_pages - 1:
        kb.add(
            Callback(
                "➡️ Вперед",
                payload={
                    "cmd": "att_page",
                    "event_id": str(event_id),
                    "page": str(page + 1),
                },
            ),
            color=KeyboardButtonColor.PRIMARY,
        )

    kb.row()
    kb.add(
        Callback("⬅️ К мероприятиям", payload={"cmd": "back_to_events"}),
        color=KeyboardButtonColor.SECONDARY,
    )

    return kb.get_json()


# --- ВЫВОД СПИСКА ПО КОМАНДЕ /resps ---
@bot.on.message(regex=r"^/resps\s*(\d+)\s*$")
async def show_responses_handler(message: Message):
    await bot.state_dispenser.delete(
        message.peer_id
    )  # СБРОС СОСТОЯНИЯ (лечит игнор команды)

    user = get_user_by_vk_id(message.from_id)
    if not user or user.role not in ("organizer", "admin"):
        return

    event_id = int(re.search(r"(\d+)", message.text).group(1))
    kb_json = generate_attendance_keyboard(event_id, page=0)

    await message.answer(
        f"👥 Список откликнувшихся на мероприятие ID {event_id}.\n"
        f"Нажми на имя, чтобы изменить статус.\n"
        f"Страница 1",
        keyboard=kb_json,
    )


async def render_attendance_list(event_id: int, peer_id: int, cmid: int = None):
    """Отрисовывает или обновляет список присутствующих."""
    responses = get_event_responses_with_details(event_id)
    text = f"👥 Список волонтеров (ID {event_id}):\n\n"
    kb = Keyboard(inline=True)

    for r in responses:
        if r.attended:
            # Отмечен (Зеленый крестик/галочка)
            kb.add(
                Callback(
                    f"✅ {r.user.full_name}",
                    payload={
                        "cmd": "toggle_attend",
                        "id": str(r.id),
                        "ev_id": str(event_id),
                    },
                ),
                color=KeyboardButtonColor.POSITIVE,
            )
        else:
            # Не отмечен (Серый/Красный)
            kb.add(
                Callback(
                    f"❌ {r.user.full_name}",
                    payload={
                        "cmd": "toggle_attend",
                        "id": str(r.id),
                        "ev_id": str(event_id),
                    },
                ),
                color=KeyboardButtonColor.NEGATIVE,
            )
        kb.row()

    kb.add(
        Callback("💾 Сохранить и закрыть", payload={"cmd": "close_attend"}),
        color=KeyboardButtonColor.PRIMARY,
    )

    text += "Нажимай на имя, чтобы отметить пришедших (✅) и отсутствующих (❌)."

    if cmid:
        await bot.api.messages.edit(
            peer_id=peer_id, cmid=cmid, message=text, keyboard=kb.get_json()
        )
    else:
        await bot.api.messages.send(
            peer_id=peer_id, message=text, keyboard=kb.get_json(), random_id=0
        )


# Нажатие на кнопку "Отклики (X)" в карточке
@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "view_resps"}
)
async def view_resps_callback(event: MessageEvent):
    await event.show_snackbar("Загрузка...")
    user = get_user_by_vk_id(event.user_id)
    # Проверяем права (хотя кнопку видят только организаторы)
    if user and user.role in ("organizer", "admin"):
        event_id = int(event.payload["id"])
        await render_attendance_list(
            event_id, event.peer_id, event.conversation_message_id
        )


# Нажатие на имя волонтера (переключение статуса)
@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    payload_contains={"cmd": "toggle_attend"},
)
async def toggle_attend_callback(event: MessageEvent):
    res_id = int(event.payload["id"])
    ev_id = int(event.payload["ev_id"])

    # Получаем текущий статус из БД
    from app.database.crud import get_session
    from app.database.models import Response

    session = get_session()
    res = session.query(Response).filter_by(id=res_id).first()
    if res:
        res.attended = not res.attended  # Инвертируем (был True -> стал False)
        session.commit()
    session.close()

    # Обновляем сообщение (моргает и меняет галочки на лету)
    await event.show_snackbar("Статус изменен")
    await render_attendance_list(ev_id, event.peer_id, event.conversation_message_id)


# Закрытие списка
@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "close_attend"}
)
async def close_attend_callback(event: MessageEvent):
    await event.show_snackbar("Сохранено!")
    await bot.api.messages.edit(
        peer_id=event.peer_id,
        cmid=event.conversation_message_id,
        message="✅ Список посещений сохранен. Вы можете закрыть это сообщение.",
    )


# --- ОБРАБОТКА НАЖАТИЯ НА КНОПКУ МЕРОПРИЯТИЯ ---
@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "show_att"}
)
async def show_att_event_handler(event: MessageEvent):
    await event.show_snackbar("Загрузка...")
    event_id = int(event.payload["event_id"])

    kb_json = generate_attendance_keyboard(event_id, page=0)

    await bot.api.messages.edit(
        peer_id=event.peer_id,
        cmid=event.conversation_message_id,
        message=f"👥 Список откликнувшихся на мероприятие ID {event_id}.\nНажми на имя, чтобы изменить статус.\nСтраница 1",
        keyboard=kb_json,
    )


# --- ОБРАБОТКА НАЖАТИЯ НА ИМЯ (ГАЛОЧКА/КРЕСТИК) ---
@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "toggle_att"}
)
async def toggle_attendance_handler(event: MessageEvent):
    await event.show_snackbar("Статус изменен!")

    response_id = int(event.payload["id"])
    page = int(event.payload["page"])
    event_id = int(event.payload["event_id"])

    session = get_session()
    resp = session.query(Response).filter_by(id=response_id).first()
    if resp:
        resp.attended = not resp.attended
        session.commit()
    session.close()

    kb_json = generate_attendance_keyboard(event_id, page=page)

    await bot.api.messages.edit(
        peer_id=event.peer_id,
        cmid=event.conversation_message_id,
        message=f"👥 Список откликнувшихся (ID {event_id}).\nНажми на имя, чтобы изменить статус.\nСтраница {page + 1}",
        keyboard=kb_json,
    )


# --- ОБРАБОТКА ЛИСТАНИЯ СТРАНИЦ ---
@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "att_page"}
)
async def page_attendance_handler(event: MessageEvent):
    await event.show_snackbar("Загрузка...")

    page = int(event.payload["page"])
    event_id = int(event.payload["event_id"])

    kb_json = generate_attendance_keyboard(event_id, page=page)

    await bot.api.messages.edit(
        peer_id=event.peer_id,
        cmid=event.conversation_message_id,
        message=f"👥 Список откликнувшихся (ID {event_id}).\nНажми на имя, чтобы изменить статус.\nСтраница {page + 1}",
        keyboard=kb_json,
    )


# --- КНОПКА НАЗАД К СПИСКУ МЕРОПРИЯТИЙ ---
@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    payload_contains={"cmd": "back_to_events"},
)
async def back_to_events_handler(event: MessageEvent):
    await event.show_snackbar("Возврат...")
    user = get_user_by_vk_id(event.user_id)
    events = get_organizer_events(user.id)

    kb = Keyboard(inline=True)
    for e in events:
        status_emoji = (
            "🟢"
            if e.status == "approved"
            else ("🟡" if e.status == "pending" else "🔴")
        )
        short_title = e.title[:20] + "..." if len(e.title) > 20 else e.title
        kb.add(
            Callback(
                f"{status_emoji} {short_title} (ID {e.id})",
                payload={"cmd": "show_att", "event_id": str(e.id)},
            ),
            color=KeyboardButtonColor.SECONDARY,
        )
        kb.row()

    await bot.api.messages.edit(
        peer_id=event.peer_id,
        cmid=event.conversation_message_id,
        message="📊 Твои мероприятия:\nНажми на кнопку, чтобы посмотреть откликнувшихся:\n\n",
        keyboard=kb.get_json(),
    )


@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "noop"}
)
async def noop_handler(event: MessageEvent):
    await event.show_snackbar("Действие недоступно.")
