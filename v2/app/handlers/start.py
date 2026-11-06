from vkbottle.bot import Message
from app.bot_instance import bot
from app.config import GROUP_ID
from app.database.crud import get_or_create_user
from app.keyboards.main_menu import get_subscription_keyboard, get_clear_keyboard,get_main_menu_keyboard

async def check_and_greet(message: Message):
    """Функция проверки подписки и приветствия (чтобы не дублировать код)."""
    user_id = message.from_id

    # 1. ПРОВЕРКА ПОДПИСКИ
    try:
        is_member = await bot.api.groups.is_member(
            group_id=GROUP_ID, 
            user_id=user_id
        )
        
        if is_member == 0:
            # Если НЕ подписан — показываем текст с кнопкой
            await message.answer(
                "❌ Чтобы пользоваться ботом, нужно сначала вступить в наше сообщество!\n\n"
                "👉 Ссылка на группу: https://vk.com/club67512708\n\n"
                "После вступления нажми на кнопку ниже 👇",
                keyboard=get_subscription_keyboard()
            )
            return
    except Exception as e:
        print(f"⚠️ Ошибка при проверке подписки: {e}")

    # 2. ПОЛУЧАЕМ ДАННЫЕ ИЗ ВК
    try:
        users_info = await bot.api.users.get(user_ids=user_id)
        if users_info:
            vk_user = users_info[0]
            first_name = vk_user.first_name
            gender = "male" if vk_user.sex == 2 else ("female" if vk_user.sex == 1 else "unknown")
        else:
            first_name = "друг"
            gender = "unknown"
    except Exception as e:
        print(f"⚠️ Ошибка при получении данных: {e}")
        first_name = "друг"
        gender = "unknown"

    # 3. СОХРАНЯЕМ В БАЗУ
    get_or_create_user(vk_id=user_id, first_name=first_name, gender=gender)

    # 4. ПРИВЕТСТВИЕ (Очищаем клавиатуру)
    await message.answer(
        f"Привет, {first_name}! 👋\n\n"
        f"Я Добробот v2.0 — помощник волонтёров ВГУИТ.\n"
        f"Рад видеть тебя в нашей команде!",
        keyboard=get_main_menu_keyboard() # <-- Выдаем меню
    )


# Обработчик команды /start
@bot.on.message(text=["/start", "начать", "Начать", "start", "Start"])
async def start_handler(message: Message):
    await check_and_greet(message)

# Обработчик кнопки "Я подписался"
@bot.on.message(text=["✅ Я подписался!"])
async def check_subscription_button(message: Message):
    await check_and_greet(message)