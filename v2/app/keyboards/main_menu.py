from vkbottle import Keyboard, Text, KeyboardButtonColor

def get_subscription_keyboard() -> str:
    return (
        Keyboard(one_time=False, inline=False)
        .add(Text("✅ Я подписался!"), color=KeyboardButtonColor.POSITIVE)
        .get_json()
    )

def get_clear_keyboard() -> str:
    return Keyboard(one_time=True, inline=False).get_json()

def get_main_menu_keyboard() -> str:
    """Главное меню (теперь только одна кнопка)."""
    return (
        Keyboard(one_time=False, inline=False)
        .add(Text("➕ Создать"), color=KeyboardButtonColor.POSITIVE)
        .get_json()
    )

def get_cancel_keyboard() -> str:
    return Keyboard(one_time=False, inline=False).add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE).get_json()

def get_skip_keyboard() -> str:
    """Кнопка пропуска без эмодзи."""
    return Keyboard(one_time=False, inline=False).add(Text("Пропустить"), color=KeyboardButtonColor.SECONDARY).get_json()