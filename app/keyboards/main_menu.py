from vkbottle import Keyboard, Text, KeyboardButtonColor


def get_gender_keyboard() -> str:
    """Клавиатура выбора пола (одноразовая)."""
    return (
        Keyboard(one_time=True, inline=False)
        .add(Text("👨 Мужской"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("👩 Женский"), color=KeyboardButtonColor.PRIMARY)
        .get_json()
    )


def get_main_menu_keyboard(role: str = "volunteer") -> str:
    """Главное меню (зависит от роли)."""
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🔍 Найти мероприятие"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("📝 Мои отклики"), color=KeyboardButtonColor.SECONDARY)
    kb.row()

    if role in ("organizer", "admin"):
        kb.add(Text("➕ Создать мероприятие"), color=KeyboardButtonColor.POSITIVE)
        kb.add(
            Text("📊 Мои мероприятия"), color=KeyboardButtonColor.SECONDARY
        )  # ← Новая кнопка
        kb.row()

    if role == "admin":
        kb.add(Text("🔔 Модерация"), color=KeyboardButtonColor.PRIMARY)
        kb.row()

    kb.add(Text("👤 Профиль"), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("⚙️ Настройки"), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()
