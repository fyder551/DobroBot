from datetime import datetime

from vkbottle import Keyboard, Text, KeyboardButtonColor
from vkbottle.bot import Message

from app.bot_instance import bot
from app.config import ADMIN_ID
from app.database.crud import get_user_by_vk_id, create_event
from app.keyboards.main_menu import get_main_menu_keyboard
from app.states import CreateEventState
import re


def get_cancel_keyboard() -> str:
    """Клавиатура с кнопкой отмены."""
    return (
        Keyboard(one_time=False, inline=False)
        .add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
        .get_json()
    )


def get_confirmation_keyboard() -> str:
    """Клавиатура предпросмотра."""
    return (
        Keyboard(one_time=False, inline=False)
        .add(Text("✅ Опубликовать"), color=KeyboardButtonColor.POSITIVE)
        .add(Text("✏️ Изменить"), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
        .get_json()
    )


# ============== СТАРТ СОЗДАНИЯ ==============


@bot.on.message(text=["➕ Создать мероприятие", "Создать мероприятие"])
async def start_create(message: Message):
    """Начало диалога создания мероприятия."""
    user = get_user_by_vk_id(message.from_id)
    if not user:
        await message.answer("Сначала напиши /start")
        return

    if user.role not in ("organizer", "admin"):
        await message.answer(
            "❌ Только организаторы и админы могут создавать мероприятия.\n"
            "Получи роль в настройках.",
            keyboard=get_main_menu_keyboard(user.role),
        )
        return

    await bot.state_dispenser.set(message.peer_id, CreateEventState.WAITING_FOR_TITLE)
    await message.answer(
        "➕ Создание мероприятия\n\n" "Шаг 1/6. Введи название мероприятия:",
        keyboard=get_cancel_keyboard(),
    )


@bot.on.message(text=["❌ Отмена"])
async def cancel_create(message: Message):
    """Отмена создания мероприятия."""
    user = get_user_by_vk_id(message.from_id)
    await bot.state_dispenser.delete(message.peer_id)
    await message.answer(
        "❌ Создание мероприятия отменено.",
        keyboard=get_main_menu_keyboard(user.role if user else "volunteer"),
    )


# ============== ШАГ 1: НАЗВАНИЕ ==============


@bot.on.message(state=CreateEventState.WAITING_FOR_TITLE)
async def process_title(message: Message):
    if not message.text:
        await message.answer("❌ Пожалуйста, отправь текстовое сообщение (название):")
        return
    title = message.text.strip()
    if not (3 <= len(title) <= 200):
        await message.answer("❌ Название от 3 до 200 символов. Попробуй снова:")
        return
    await bot.state_dispenser.set(
        message.peer_id, CreateEventState.WAITING_FOR_DATE, title=title
    )
    await message.answer(
        "Отлично! Теперь введи дату в формате ДД.ММ.ГГГГ (например, 25.10.2026):"
    )


@bot.on.message(state=CreateEventState.WAITING_FOR_DATE)
async def process_date(message: Message):
    if not message.text:
        await message.answer("❌ Пожалуйста, отправь текстовое сообщение с датой:")
        return
    text = message.text.strip()
    try:
        event_date = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("❌ Неверный формат. Введи дату как ДД.ММ.ГГГГ:")
        return
    today = datetime.now().date()
    if event_date < today:
        await message.answer("❌ Дата не может быть в прошлом:")
        return
    if (event_date - today).days > 365:
        await message.answer("❌ Слишком далеко! Максимум на год вперед:")
        return
    state = await bot.state_dispenser.get(message.peer_id)
    await bot.state_dispenser.set(
        message.peer_id,
        CreateEventState.WAITING_FOR_TIME,
        title=state.payload["title"],
        date=text,
    )
    await message.answer("Введи время НАЧАЛА в формате ЧЧ:ММ (например, 14:00):")


@bot.on.message(state=CreateEventState.WAITING_FOR_TIME)
async def process_time(message: Message):
    if not message.text:
        await message.answer("❌ Пожалуйста, отправь время текстом:")
        return
    text = message.text.strip()
    if not re.match(r"^\d{2}:\d{2}$", text):
        await message.answer(
            "❌ Неверный формат. Введи время ровно как ЧЧ:ММ (например, 15:00):"
        )
        return
    try:
        event_time = datetime.strptime(text, "%H:%M").time()
    except ValueError:
        await message.answer("❌ Такого времени не существует. Введи корректное время:")
        return
    state = await bot.state_dispenser.get(message.peer_id)
    payload = state.payload
    event_date = datetime.strptime(payload["date"], "%d.%m.%Y").date()
    if event_date == datetime.now().date() and event_time <= datetime.now().time():
        await message.answer("❌ Время не может быть в прошлом. Введи будущее время:")
        return
    await bot.state_dispenser.set(
        message.peer_id, CreateEventState.WAITING_FOR_LOCATION, **payload, time=text
    )
    await message.answer("📝 Где будет проходить мероприятие? (Введи место):")


@bot.on.message(state=CreateEventState.WAITING_FOR_LOCATION)
async def process_location(message: Message):
    if not message.text:
        await message.answer("❌ Пожалуйста, напиши место текстом:")
        return
    location = message.text.strip()
    if len(location) < 3:
        await message.answer("❌ Слишком короткое место. Попробуй снова:")
        return
    state = await bot.state_dispenser.get(message.peer_id)
    await bot.state_dispenser.set(
        message.peer_id,
        CreateEventState.WAITING_FOR_DESCRIPTION,
        **state.payload,
        location=location,
    )
    await message.answer("📝 Напиши, чем будут заниматься волонтеры:")


@bot.on.message(state=CreateEventState.WAITING_FOR_DESCRIPTION)
async def process_description(message: Message):
    if not message.text:
        await message.answer("❌ Пожалуйста, отправь описание текстом:")
        return
    description = message.text.strip()
    if len(description) < 10:
        await message.answer("❌ Описание слишком короткое (мин. 10 символов):")
        return
    state = await bot.state_dispenser.get(message.peer_id)
    await bot.state_dispenser.set(
        message.peer_id,
        CreateEventState.WAITING_FOR_MAX_VOLUNTEERS,
        **state.payload,
        description=description,
    )
    await message.answer(
        "Сколько волонтёров требуется? (Напиши число или слово «Все»):"
    )


@bot.on.message(state=CreateEventState.WAITING_FOR_MAX_VOLUNTEERS)
async def process_max_volunteers(message: Message):
    if not message.text:
        await message.answer("❌ Пожалуйста, напиши число или слово «Все»:")
        return
    max_vol = message.text.strip().lower()

    # ПРОВЕРКА: Либо "все", либо число от 1 до 1000
    if max_vol == "все":
        pass  # Оставляем как есть
    elif max_vol.isdigit():
        # Проверяем, что нет ведущих нулей (кроме самого числа "0", но у нас от 1)
        if max_vol.startswith("0") and len(max_vol) > 1:
            await message.answer(
                "❌ Некорректное количество. Введи реальное число или слово «Все»."
            )
            return

        if not (1 <= int(max_vol) <= 1000):
            await message.answer(
                "❌ Некорректное количество. Введи реальное число или слово «Все»."
            )
            return

    state = await bot.state_dispenser.get(message.peer_id)
    await bot.state_dispenser.set(
        message.peer_id,
        CreateEventState.WAITING_FOR_GENDER,
        **state.payload,
        max_volunteers=max_vol,
    )

    kb = (
        Keyboard(one_time=True, inline=False)
        .add(Text("👥 Любые"))
        .add(Text("👦 Мальчики"))
        .add(Text("👧 Девочки"))
        .get_json()
    )
    await message.answer("Кто требуется на мероприятие?", keyboard=kb)


@bot.on.message(state=CreateEventState.WAITING_FOR_GENDER)
async def process_gender_req(message: Message):
    try:
        # Убираем эмодзи и приводим к нижнему регистру
        text = message.text.lower()
        text = (
            text.replace("😎", "")
            .replace("👦", "")
            .replace("👧", "")
            .replace("👥", "")
            .strip()
        )

        if "мальчик" in text:
            gender = "male"
        elif "девочк" in text:
            gender = "female"
        elif "любые" in text or "любой" in text:
            gender = "all"
        else:
            await message.answer("❌ Пожалуйста, выбери вариант на кнопках ниже.")
            return

        user = get_user_by_vk_id(message.from_id)
        if not user:
            return

        state = await bot.state_dispenser.get(message.peer_id)
        payload = state.payload or {}
        auto_contacts = f"vk.com/id{user.vk_id}"

        await bot.state_dispenser.set(
            message.peer_id,
            CreateEventState.WAITING_FOR_CHAT_LINK,
            **payload,
            gender_required=gender,
            contacts=auto_contacts,
        )

        await message.answer(
            "Дай ссылку на общий чат или форму для связи (или напиши «Нет»):",
            keyboard=get_cancel_keyboard(),
        )
    except Exception:
        import traceback

        print("\n=== ОШИБКА ПРИ ВЫБОРЕ ПОЛА ===")
        traceback.print_exc()
        print("==============================\n")
        await message.answer("❌ Произошла ошибка на сервере. Проверь консоль VS Code.")


# ============== ШАГ 9: ССЫЛКА НА ЧАТ ==============
@bot.on.message(state=CreateEventState.WAITING_FOR_CHAT_LINK)
async def process_chat_link(message: Message):
    link = message.text.strip()
    # Очищаем ввод от точек и пробелов для проверки
    clean_link = link.lower().replace(".", "").strip()

    # Если написали отказ — сохраняем пустоту
    if clean_link in ["нет", "no", "-"]:
        link = None
    # Если это не отказ и не начинается с http — выдаем ошибку
    elif not link.startswith("http"):
        await message.answer(
            "❌ Ссылка должна начинаться с http:// или https://. Или напиши «Нет»."
        )
        return
    state = await bot.state_dispenser.get(message.peer_id)
    payload = state.payload or {}

    await bot.state_dispenser.set(
        message.peer_id,
        CreateEventState.WAITING_FOR_BONUS,
        title=payload.get("title"),
        date=payload.get("date"),
        time=payload.get("time"),
        location=payload.get("location"),
        description=payload.get("description"),
        max_volunteers=payload.get("max_volunteers"),
        gender_required=payload.get("gender_required"),
        contacts=payload.get("contacts"),
        chat_link=link,
    )
    await message.answer(
        "Шаг 10/10. Какие плюшки/бонусы получат волонтеры? (или напиши «Нет»):",
        keyboard=get_cancel_keyboard(),
    )


# ============== ШАГ 10: ПЛЮШКИ + ПРЕДПРОСМОТР ==============
@bot.on.message(state=CreateEventState.WAITING_FOR_BONUS)
async def process_bonus(message: Message):
    bonus = message.text.strip()
    if bonus.lower().replace(".", "") in ["нет", "no", "-"]:
        bonus = None
    state = await bot.state_dispenser.get(message.peer_id)
    payload = state.payload or {}

    await bot.state_dispenser.set(
        message.peer_id,
        CreateEventState.WAITING_FOR_CONFIRMATION,
        title=payload.get("title"),
        date=payload.get("date"),
        time=payload.get("time"),
        location=payload.get("location"),
        description=payload.get("description"),
        max_volunteers=payload.get("max_volunteers"),
        gender_required=payload.get("gender_required"),
        contacts=payload.get("contacts"),
        chat_link=payload.get("chat_link"),
        bonus_info=bonus,
    )

    gender_ru = {
        "all": "👥 Любые",
        "male": "👦 Только мальчики",
        "female": "👧 Только девочки",
    }.get(payload.get("gender_required"), "👥 Любые")

    preview_text = (
        f"📋 Предпросмотр мероприятия:\n\n"
        f"📌 {payload.get('title')}\n"
        f"📅 {payload.get('date')} в {payload.get('time')}\n"
        f"📍 {payload.get('location')}\n"
        f"📝 {payload.get('description')}\n\n"
        f"👥 Нужно: {payload.get('max_volunteers')} чел. ({gender_ru})\n"
    )
    if payload.get("chat_link"):
        preview_text += f"🔗 Чат: {payload.get('chat_link')}\n"
    if bonus:
        preview_text += f"🎁 Бонусы: {bonus}\n"
    preview_text += f"📞 Связь: {payload.get('contacts')}\n\nВсё верно?"

    await message.answer(preview_text, keyboard=get_confirmation_keyboard())


# ============== ОТПРАВКА НА МОДЕРАЦИЮ ==============


@bot.on.message(
    state=CreateEventState.WAITING_FOR_CONFIRMATION,
    text=["✅ Опубликовать"],
)
async def publish_event(message: Message):
    user = get_user_by_vk_id(message.from_id)
    if not user:
        return

    state = await bot.state_dispenser.get(message.peer_id)
    payload = state.payload or {}

    # Парсим дату и время
    date_obj = datetime.strptime(payload.get("date"), "%d.%m.%Y").date()
    time_obj = datetime.strptime(payload.get("time"), "%H:%M").time()

    # Создаём мероприятие
    event = create_event(
        organizer_id=user.id,
        title=payload.get("title"),
        date=date_obj,
        time_=time_obj,
        location=payload.get("location"),
        description=payload.get("description"),
        max_volunteers=payload.get("max_volunteers"),
        gender_required=payload.get("gender_required"),
        contacts=payload.get("contacts"),
        chat_link=payload.get("chat_link"),
        bonus_info=payload.get("bonus_info"),
    )

    await bot.state_dispenser.delete(message.peer_id)

    await message.answer(
        f"✅ Мероприятие «{event.title}» отправлено на модерацию.\n"
        f"После проверки админом оно появится в поиске.",
        keyboard=get_main_menu_keyboard(user.role),
    )

    # Уведомление админу
    if user.vk_id != ADMIN_ID:
        try:
            await bot.api.messages.send(
                user_id=ADMIN_ID,
                message=(
                    f"🔔 Новое мероприятие на модерацию!\n\n"
                    f"📌 {event.title}\n"
                    f"📅 {payload.get('date')} в {payload.get('time')}\n"
                    f"📍 {payload.get('location')}\n\n"
                    f"Чтобы проверить, нажми кнопку «🔔 Модерация» в главном меню."
                ),
                random_id=0,
            )
        except Exception as e:
            print(f"⚠️ Не удалось отправить уведомление админу: {e}")


@bot.on.message(
    state=CreateEventState.WAITING_FOR_CONFIRMATION,
    text=["✏️ Изменить"],
)
async def edit_event(message: Message):
    await bot.state_dispenser.set(message.peer_id, CreateEventState.WAITING_FOR_TITLE)
    await message.answer(
        "✏️ Начнём заново.\n\n" "Шаг 1/6. Введи название мероприятия:",
        keyboard=get_cancel_keyboard(),
    )
