from vkbottle import BaseStateGroup


class RegistrationState(BaseStateGroup):
    """Состояния регистрации пользователя."""

    WAITING_FOR_GENDER = "waiting_for_gender"
    WAITING_FOR_FULL_NAME = "waiting_for_full_name"


class MenuState(BaseStateGroup):
    """Состояния главного меню."""

    IN_MENU = "in_menu"


class SettingsState(BaseStateGroup):
    """Состояния настроек."""

    WAITING_FOR_ROLE_CODE = "waiting_for_role_code"
    WAITING_FOR_NEW_NAME = "waiting_for_new_name"


class CreateEventState(BaseStateGroup):
    """Состояния создания мероприятия."""

    WAITING_FOR_TITLE = "waiting_for_title"
    WAITING_FOR_DATE = "waiting_for_date"
    WAITING_FOR_TIME = "waiting_for_time"
    WAITING_FOR_END_TIME = "waiting_for_end_time"
    WAITING_FOR_LOCATION = "waiting_for_location"
    WAITING_FOR_DESCRIPTION = "waiting_for_description"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    WAITING_FOR_MAX_VOLUNTEERS = "waiting_for_max_volunteers"
    WAITING_FOR_GENDER = "waiting_for_gender"
    WAITING_FOR_CHAT_LINK = "waiting_for_chat_link"  # <-- НОВОЕ
    WAITING_FOR_BONUS = "waiting_for_bonus"  # <-- НОВОЕ


class SearchState(BaseStateGroup):
    """Состояния поиска мероприятий."""

    BROWSING = "browsing_events"
