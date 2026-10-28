from vkbottle.bot import Message

from app.bot_instance import bot
from app.database.crud import (
    get_user_by_vk_id,
    create_user,
)
from app.keyboards.main_menu import get_gender_keyboard, get_main_menu_keyboard
from app.states import RegistrationState
from app.utils.validators import validate_full_name


def get_short_name(full_name: str) -> str:
    """Достаёт имя из ФИО (второе слово)."""
    parts = full_name.split()
    return parts[1] if len(parts) >= 2 else full_name


@bot.on.message(text=["/start", "Начать", "начать", "start", "Start", "Старт"])
async def start_handler(message: Message):
    await bot.state_dispenser.delete(message.peer_id)
    """Обработчик команды /start."""
    user = get_user_by_vk_id(message.from_id)

    # Пользователь уже зарегистрирован
    if user and user.full_name:
        await message.answer(
            f"С возвращением, {get_short_name(user.full_name)}! 👋\n\n"
            "Вот главное меню:",
            keyboard=get_main_menu_keyboard(user.role),
        )
        return

    # Получаем имя из ВК для приветствия
    user_info = await bot.api.users.get(user_ids=message.from_id)
    vk_first_name = user_info[0].first_name if user_info else "друг"

    # Устанавливаем состояние: ждём выбор пола
    await bot.state_dispenser.set(message.peer_id, RegistrationState.WAITING_FOR_GENDER)

    await message.answer(
        f"Привет, {vk_first_name}! 👋\n\n"
        "Я ДоброБот — помогаю волонтёрам ВГУИТ.\n\n"
        "Для начала давай познакомимся.\n"
        "Укажи свой пол:",
        keyboard=get_gender_keyboard(),
    )


@bot.on.message(
    state=RegistrationState.WAITING_FOR_GENDER,
    text=["👨 Мужской", "Мужской", "мужской", "м"],
)
async def handle_gender_male(message: Message):
    await _process_gender(message, "male")


@bot.on.message(
    state=RegistrationState.WAITING_FOR_GENDER,
    text=["👩 Женский", "Женский", "женский", "ж"],
)
async def handle_gender_female(message: Message):
    await _process_gender(message, "female")


async def _process_gender(message: Message, gender: str):
    """Сохраняем пол во временном хранилище состояния."""
    await bot.state_dispenser.set(
        message.peer_id,
        RegistrationState.WAITING_FOR_FULL_NAME,
        gender=gender,
    )
    await message.answer(
        "Отлично! ✅\n\n" "Теперь введи своё ФИО\n" "Например: Иванов Иван Иванович"
    )


@bot.on.message(state=RegistrationState.WAITING_FOR_GENDER)
async def fallback_gender(message: Message):
    """Если пользователь пишет что-то не то вместо выбора пола."""
    await message.answer(
        "Пожалуйста, выбери пол с помощью кнопок ниже 👇",
        keyboard=get_gender_keyboard(),
    )


@bot.on.message(state=RegistrationState.WAITING_FOR_FULL_NAME)
async def handle_full_name(message: Message):
    """Обрабатываем ввод ФИО с проверкой."""
    text = message.text.strip()
    words = text.split()

    # Получаем пол из состояния
    state_peer = await bot.state_dispenser.get(message.peer_id)
    gender = "male"
    if state_peer and state_peer.payload:
        gender = state_peer.payload.get("gender", "male")

    # Валидация
    is_valid, error_msg = validate_full_name(text, gender)

    if not is_valid:
        await message.answer(
            f"❌ {error_msg}\n\n" "Введи ФИО снова.\n" "Пример: Иванов Иван Иванович"
        )
        return

    # Если валидатор вернул предупреждение (имя не в списке) — показываем, но принимаем
    if error_msg:
        await message.answer(error_msg)

    # Получаем имя из ВК
    user_info = await bot.api.users.get(user_ids=message.from_id)
    vk_first_name = user_info[0].first_name if user_info else "друг"

    # Создаём пользователя
    create_user(
        vk_id=message.from_id,
        vk_first_name=vk_first_name,
        gender=gender,
        full_name=text,
    )

    # Сбрасываем состояние
    await bot.state_dispenser.delete(message.peer_id)

    # Показываем меню
    short_name = words[1]
    await message.answer(
        f"Отлично, {short_name}! Теперь ты в системе. ✅\n\n" "Вот главное меню:",
        keyboard=get_main_menu_keyboard("volunteer"),
    )

    # Если валидатор вернул предупреждение (имя не в списке) — показываем, но принимаем
    if error_msg:
        await message.answer(error_msg)

    # Получаем имя из ВК
    user_info = await bot.api.users.get(user_ids=message.from_id)
    vk_first_name = user_info[0].first_name if user_info else "друг"

    # Создаём пользователя
    create_user(
        vk_id=message.from_id,
        vk_first_name=vk_first_name,
        gender=gender,
        full_name=text,
    )

    # Сбрасываем состояние
    await bot.state_dispenser.delete(message.peer_id)

    # Показываем меню
    short_name = text.split()[1]
    await message.answer(
        f"Отлично, {short_name}! Теперь ты в системе. ✅\n\n" "Вот главное меню:",
        keyboard=get_main_menu_keyboard("volunteer"),
    )

    # Получаем пол из состояния
    state_peer = await bot.state_dispenser.get(message.peer_id)
    gender = "male"
    if state_peer and state_peer.payload:
        gender = state_peer.payload.get("gender", "male")

    # Получаем имя из ВК
    user_info = await bot.api.users.get(user_ids=message.from_id)
    vk_first_name = user_info[0].first_name if user_info else "друг"

    # Создаём пользователя в БД
    create_user(
        vk_id=message.from_id,
        vk_first_name=vk_first_name,
        gender=gender,
        full_name=text,
    )

    # Сбрасываем состояние
    await bot.state_dispenser.delete(message.peer_id)

    # Показываем главное меню
    short_name = words[1]  # Имя — второе слово
    await message.answer(
        f"Отлично, {short_name}! Теперь ты в системе. ✅\n\n" "Вот главное меню:",
        keyboard=get_main_menu_keyboard("volunteer"),
    )
