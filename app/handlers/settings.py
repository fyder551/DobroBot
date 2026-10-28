from vkbottle import Keyboard, Text, KeyboardButtonColor
from vkbottle.bot import Message

from app.bot_instance import bot
from app.config import ADMIN_CODE, ORGANIZER_CODE
from app.database.crud import (
    get_user_by_vk_id,
    change_role,
    downgrade_role,
    can_return_to_previous,
)
from app.keyboards.main_menu import get_main_menu_keyboard
from app.states import SettingsState
from app.database.crud import update_user_notifications


def get_settings_keyboard(role: str) -> str:
    """Клавиатура настроек (зависит от роли)."""
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🔑 Сменить роль"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🔔 Уведомления"), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("⬅️ В главное меню"), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def get_role_choice_keyboard(role: str) -> str:
    """Меню выбора роли (показывает доступные роли)."""
    kb = Keyboard(one_time=True, inline=False)
    if role == "admin":
        # Админ может свободно переключаться
        kb.add(Text("👤 Стать волонтёром"), color=KeyboardButtonColor.SECONDARY)
        kb.add(Text("🎯 Стать организатором"), color=KeyboardButtonColor.SECONDARY)
    elif role == "organizer":
        # Организатор может стать волонтёром (без кода) или админом (с кодом)
        kb.add(Text("👤 Стать волонтёром"), color=KeyboardButtonColor.SECONDARY)
        kb.add(Text("👑 Стать админом"), color=KeyboardButtonColor.PRIMARY)
    else:
        # Волонтёр может стать организатором или админом только по коду
        kb.add(Text("🎯 Стать организатором"), color=KeyboardButtonColor.SECONDARY)
        kb.add(Text("👑 Стать админом"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("⬅️ Назад"), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


@bot.on.message(text=["⚙️ Настройки", "Настройки"])
async def settings_handler(message: Message):
    """Главное меню настроек."""
    await bot.state_dispenser.delete(message.peer_id)
    user = get_user_by_vk_id(message.from_id)
    if not user:
        await message.answer("Сначала напиши /start")
        return

    role_ru = {
        "volunteer": "Волонтёр",
        "organizer": "Организатор",
        "admin": "Администратор",
    }.get(user.role, "Волонтёр")

    await message.answer(
        f"⚙️ Настройки\n\n" f"Твоя текущая роль: {role_ru}",
        keyboard=get_settings_keyboard(user.role),
    )


@bot.on.message(text=["🔑 Сменить роль"])
async def change_role_handler(message: Message):
    """Открывает меню выбора роли."""
    user = get_user_by_vk_id(message.from_id)
    if not user:
        return

    await message.answer(
        "Какую роль ты хочешь получить?",
        keyboard=get_role_choice_keyboard(user.role),
    )


@bot.on.message(text=["👤 Стать волонтёром"])
async def become_volunteer(message: Message):
    """Понижение до волонтёра (без кода)."""
    user = get_user_by_vk_id(message.from_id)
    if not user:
        return

    if user.role == "volunteer":
        await message.answer("Ты уже волонтёр 😊")
        return

    # Понижаем с сохранением previous_role
    downgrade_role(message.from_id, "volunteer")

    await message.answer(
        "✅ Ты стал волонтёром.\n\n"
        "⏱️ У тебя есть 2 минуты, чтобы вернуться в прежнюю роль без кода.",
        keyboard=get_main_menu_keyboard("volunteer"),
    )


@bot.on.message(text=["🎯 Стать организатором", "👑 Стать админом"])
async def ask_for_code(message: Message):
    """Запрашивает код для повышения роли."""
    user = get_user_by_vk_id(message.from_id)
    if not user:
        return

    new_role = "organizer" if "организатором" in message.text else "admin"

    # Проверяем: можно ли вернуться в previous_role без кода
    if user.role == "volunteer" and can_return_to_previous(message.from_id):
        if user.previous_role == new_role:
            change_role(message.from_id, new_role)
            role_ru = "Организатор" if new_role == "organizer" else "Администратор"
            await message.answer(
                f"✅ Ты снова {role_ru}!",
                keyboard=get_main_menu_keyboard(new_role),
            )
            return

    # Иначе — просим код
    await bot.state_dispenser.set(
        message.peer_id,
        SettingsState.WAITING_FOR_ROLE_CODE,
        target_role=new_role,
    )
    await message.answer(
        "🔑 Введи ключ-код для получения роли.\n\n" "(Если передумал — напиши /start)"
    )


@bot.on.message(state=SettingsState.WAITING_FOR_ROLE_CODE)
async def process_role_code(message: Message):
    """Проверяет введённый ключ-код."""
    if message.text.startswith("/"):
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer("Действие отменено.")
        return
    text = message.text.strip()

    state_peer = await bot.state_dispenser.get(message.peer_id)
    target_role = "organizer"
    if state_peer and state_peer.payload:
        target_role = state_peer.payload.get("target_role", "organizer")

    # Определяем, какой код нужен
    expected_code = ORGANIZER_CODE if target_role == "organizer" else ADMIN_CODE

    if text == expected_code:
        change_role(message.from_id, target_role)
        await bot.state_dispenser.delete(message.peer_id)
        role_ru = "Организатор" if target_role == "organizer" else "Администратор"
        await message.answer(
            f"✅ Готово! Ты теперь {role_ru}.",
            keyboard=get_main_menu_keyboard(target_role),
        )
    else:
        await message.answer(
            "❌ Неверный код. Попробуй ещё раз или напиши /start для отмены."
        )


@bot.on.message(text=["⬅️ В главное меню", "⬅️ Назад"])
async def back_to_menu(message: Message):
    """Возвращает в главное меню."""
    user = get_user_by_vk_id(message.from_id)
    if not user:
        return
    await message.answer(
        "Главное меню:",
        keyboard=get_main_menu_keyboard(user.role),
    )


@bot.on.message(text=["🔔 Уведомления"])
async def toggle_notifications(message: Message):
    user = get_user_by_vk_id(message.from_id)
    if not user:
        return

    new_state = not user.notifications_enabled
    update_user_notifications(message.from_id, new_state)

    status = "ВКЛЮЧЕНЫ ✅" if new_state else "ВЫКЛЮЧЕНЫ ❌"
    await message.answer(
        f"Уведомления о новых мероприятиях теперь {status}",
        keyboard=get_settings_keyboard(user.role),  # ваша клавиатура настроек
    )
