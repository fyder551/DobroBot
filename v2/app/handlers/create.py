import re
from datetime import datetime

from vkbottle import Keyboard, Text, KeyboardButtonColor, Callback, OpenLink
from vkbottle.bot import Message
from app.database.crud import get_session
from app.database.models import Event

from app.bot_instance import bot
from app.database.crud import get_user_by_vk_id, create_event,update_event_cmid
from app.keyboards.main_menu import get_cancel_keyboard, get_skip_keyboard, get_main_menu_keyboard
from app.states import CreateEventState,AnnouncementState
from app.config import CHAT_ID, GROUP_ID
import random
import asyncio


# --- СТАРТ СОЗДАНИЯ ---
@bot.on.message(regex=r"(?i).*создать.*")
async def start_create(message: Message):
    if message.peer_id > 2000000000: return
    
    await bot.state_dispenser.delete(message.peer_id) 
    await bot.state_dispenser.set(message.peer_id, CreateEventState.CHOOSING_TYPE)
    
    kb = (
        Keyboard(one_time=False, inline=False)
        .add(Text("📅 Мероприятие"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("📢 Объявление"), color=KeyboardButtonColor.SECONDARY)
        .row().add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
    )
    await message.answer("Что ты хочешь создать?", keyboard=kb.get_json())


# --- ВЫБОР: МЕРОПРИЯТИЕ ИЛИ ОБЪЯВЛЕНИЕ ---
@bot.on.message(state=CreateEventState.CHOOSING_TYPE, text=["📅 Мероприятие"])
async def choice_event(message: Message):
    await bot.state_dispenser.set(message.peer_id, CreateEventState.TITLE)
    kb = Keyboard(one_time=False, inline=False).add(Text("❗Нужны волонтеры❗"), color=KeyboardButtonColor.PRIMARY).row().add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
    await message.answer("📝 Шаг 1/9. Введи название мероприятия:", keyboard=kb.get_json())

@bot.on.message(state=CreateEventState.CHOOSING_TYPE, text=["📢 Объявление"])
async def choice_announcement(message: Message):
    await bot.state_dispenser.set(message.peer_id, AnnouncementState.PHOTO)
    await message.answer(
        "Прикрепи фото к объявлению (от 1 до 5). Если фото не нужно, напиши «Пропустить».",
        keyboard=get_skip_keyboard()
    )

# --- ОБЪЯВЛЕНИЕ: ФОТО ---
@bot.on.message(state=AnnouncementState.PHOTO)
async def process_ann_photo(message: Message):
    photo_attachment = None
    if message.text and "пропустить" in message.text.lower():
        pass 
    elif message.attachments:
        photos = []
        for att in message.attachments:
            if att.photo:
                access_key = getattr(att.photo, 'access_key', '')
                photo_str = f"photo{att.photo.owner_id}_{att.photo.id}" + (f"_{access_key}" if access_key else "")
                photos.append(photo_str)
        if not photos:
            await message.answer("❌ В прикрепленных файлах нет фотографий. Отправь фото или напиши «Пропустить».")
            return
        if len(photos) > 5:
            await message.answer("❌ Можно прикрепить не более 5 фотографий.")
            return
        photo_attachment = ",".join(photos)
    else:
        await message.answer("❌ Ты не прикрепил фото. Попробуй снова или напиши «Пропустить».")
        return
            
    await bot.state_dispenser.set(message.peer_id, AnnouncementState.TITLE, photo=photo_attachment)
    await message.answer("Напиши заголовок объявления (например: 🔥 Хочешь стать волонтером?):")

# --- ОБЪЯВЛЕНИЕ: ЗАГОЛОВОК ---
@bot.on.message(state=AnnouncementState.TITLE)
async def process_ann_title(message: Message):
    if not message.text:
        await message.answer("Пожалуйста, отправь текст заголовка.")
        return
        
    title = message.text.strip()
    state = await bot.state_dispenser.get(message.peer_id)
    p = state.payload or {}
    
    await bot.state_dispenser.set(message.peer_id, AnnouncementState.TEXT, photo=p.get("photo"), title=title)
    await message.answer("Теперь напиши основной текст объявления (можешь использовать переносы строк и эмодзи):")

# --- ОБЪЯВЛЕНИЕ: ТЕКСТ ---
@bot.on.message(state=AnnouncementState.TEXT)
async def process_ann_text(message: Message):
    if not message.text:
        await message.answer("Пожалуйста, отправь текст объявления.")
        return
        
    text = message.text.strip()
    state = await bot.state_dispenser.get(message.peer_id)
    p = state.payload or {}
    
    await bot.state_dispenser.set(message.peer_id, AnnouncementState.PREVIEW, photo=p.get("photo"), title=p.get("title"), text=text)
    
    # Предпросмотр (без тегов, чтобы выглядело чисто)
    preview_text = f"📋 <b>Предпросмотр объявления:</b>\n\n<b>{p.get('title')}</b>\n\n{text}"
    if p.get("photo"):
        preview_text += "\n\n(С фотографией)"
        
    kb = (
        Keyboard(one_time=False, inline=False)
        .add(Text("✅ Опубликовать"), color=KeyboardButtonColor.POSITIVE)
        .add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
    )
    # Отправляем предпросмотр с parse_mode="HTML"
    await message.answer(preview_text, keyboard=kb.get_json(), parse_mode="HTML")

@bot.on.message(regex=r"(?i).*отмена.*")
async def cancel_create(message: Message):
    if message.peer_id > 2000000000:
        return 
    await bot.state_dispenser.delete(message.peer_id)
    await message.answer("❌ Создание отменено.", keyboard=get_main_menu_keyboard())


# --- ШАГ 1: НАЗВАНИЕ ---
@bot.on.message(state=CreateEventState.TITLE)
async def process_title(message: Message):
    if message.peer_id > 2000000000:
        return 
    if not message.text:
        await message.answer("Пожалуйста, отправь текст.")
        return
        
    title = message.text.strip()
    if len(title) < 3:
        await message.answer("Название слишком короткое. Введи нормально:")
        return

    # ДОБАВИЛИ or {} ДЛЯ ЗАЩИТЫ ОТ ПУСТОГО payload
    await bot.state_dispenser.set(message.peer_id, CreateEventState.MAX_VOLUNTEERS, title=title)
    await message.answer("Шаг 2/9. Сколько нужно волонтеров? (Напиши число или «Все»):", keyboard=get_cancel_keyboard())

# --- ШАГ 2: КОЛИЧЕСТВО ---
@bot.on.message(state=CreateEventState.MAX_VOLUNTEERS)
async def process_max_vol(message: Message):
    if message.peer_id > 2000000000:
        return
    if "отмена" in message.text.lower():
        await cancel_create(message)
        return
    text = message.text.strip().lower()
    if text != "все" and not text.isdigit():
        await message.answer("Введи число или слово «Все».")
        return

    state = await bot.state_dispenser.get(message.peer_id)
    # ДОБАВИЛИ or {} СЮДА
    await bot.state_dispenser.set(message.peer_id, CreateEventState.GENDER, **(state.payload or {}), max_vol=text)
    
    kb = (
        Keyboard(one_time=True, inline=False)
        .add(Text("Любые"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Мальчики"), color=KeyboardButtonColor.SECONDARY)
        .add(Text("Девочки"), color=KeyboardButtonColor.SECONDARY)
        .get_json()
    )
    await message.answer("Шаг 3/9. Кто требуется?", keyboard=kb)


# --- ШАГ 3: ПОЛ ---
@bot.on.message(state=CreateEventState.GENDER)
async def process_gender(message: Message):
    if message.peer_id > 2000000000:
        return
    text = message.text.lower()
    if "мальчик" in text: gender = "male"
    elif "девочк" in text: gender = "female"
    elif "любы" in text: gender = "all"
    else:
        await message.answer("Выбери вариант на кнопках.")
        return

    state = await bot.state_dispenser.get(message.peer_id)
    # ДОБАВИЛИ or {}
    await bot.state_dispenser.set(message.peer_id, CreateEventState.DATE, **(state.payload or {}), gender=gender)
    await message.answer("Шаг 4/9. Введи дату (ДД.ММ или ДД.ММ.ГГГГ):", keyboard=get_cancel_keyboard())

# --- ШАГ 4: ДАТА ---
@bot.on.message(state=CreateEventState.DATE)
async def process_date(message: Message):
    if message.peer_id > 2000000000:
        return
    text = message.text.strip()
    try:
        if len(text.split('.')) == 2:
            event_date = datetime.strptime(f"{text}.{datetime.now().year}", "%d.%m.%Y").date()
        else:
            event_date = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("Неверный формат. Введи ДД.ММ или ДД.ММ.ГГГГ:")
        return

    if event_date < datetime.now().date():
        await message.answer("Дата не может быть в прошлом. Введи будущую дату:")
        return

    state = await bot.state_dispenser.get(message.peer_id)
    # ДОБАВИЛИ or {}
    await bot.state_dispenser.set(message.peer_id, CreateEventState.TIME_START, **(state.payload or {}), date=text)
    await message.answer("Шаг 5/9. Введи время НАЧАЛА (например, 14:00):", keyboard=get_cancel_keyboard())

# --- ШАГ 5: ВРЕМЯ НАЧАЛА ---
@bot.on.message(state=CreateEventState.TIME_START)
async def process_time_start(message: Message):
    if message.peer_id > 2000000000:
        return
    text = message.text.strip()
    if not re.match(r"^\d{1,2}:\d{2}$", text):
        await message.answer("Неверный формат. Введи ЧЧ:ММ:")
        return

    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        await message.answer("Такого времени не существует:")
        return

    state = await bot.state_dispenser.get(message.peer_id)
    # ДОБАВИЛИ or {}
    await bot.state_dispenser.set(message.peer_id, CreateEventState.TIME_END, **(state.payload or {}), time_start=text)
    await message.answer("Шаг 6/9. Введи время ОКОНЧАНИЯ (ЧЧ:ММ):", keyboard=get_cancel_keyboard())

# --- ШАГ 6: ВРЕМЯ ОКОНЧАНИЯ ---
@bot.on.message(state=CreateEventState.TIME_END)
async def process_time_end(message: Message):
    if message.peer_id > 2000000000:
        return
    text = message.text.strip()
    if not re.match(r"^\d{1,2}:\d{2}$", text):
        await message.answer("Неверный формат. Введи ЧЧ:ММ:")
        return

    try:
        time_end = datetime.strptime(text, "%H:%M").time()
    except ValueError:
        await message.answer("Такого времени не существует:")
        return

    state = await bot.state_dispenser.get(message.peer_id)
    time_start_obj = datetime.strptime(state.payload["time_start"], "%H:%M").time()

    if time_end <= time_start_obj:
        await message.answer("Время окончания должно быть позже времени начала! Введи снова:")
        return

    # ДОБАВИЛИ or {}
    await bot.state_dispenser.set(message.peer_id, CreateEventState.LOCATION, **(state.payload or {}), time_end=text)
    await message.answer("Шаг 7/9. Введи место проведения:", keyboard=get_cancel_keyboard())

# --- ШАГ 7: МЕСТО ---
@bot.on.message(state=CreateEventState.LOCATION)
async def process_location(message: Message):
    if message.peer_id > 2000000000:
        return
    state = await bot.state_dispenser.get(message.peer_id)
    # ДОБАВИЛИ or {}
    await bot.state_dispenser.set(message.peer_id, CreateEventState.DESCRIPTION, **(state.payload or {}), location=message.text.strip())
    await message.answer("Шаг 8/9. Опиши функционал (что будут делать волонтеры?):", keyboard=get_cancel_keyboard())

# --- ШАГ 8: ФУНКЦИОНАЛ ---
@bot.on.message(state=CreateEventState.DESCRIPTION)
async def process_description(message: Message):
    if message.peer_id > 2000000000:
        return
    state = await bot.state_dispenser.get(message.peer_id)
    # ДОБАВИЛИ or {}
    await bot.state_dispenser.set(message.peer_id, CreateEventState.BONUS, **(state.payload or {}), description=message.text.strip())
    await message.answer("Шаг 9/9. Какие бонусы/плюшки? (Или напиши «Нет»)", keyboard=get_skip_keyboard())

# --- ШАГ 9: ПЛЮШКИ (ОПЦИОНАЛЬНО) ---
@bot.on.message(state=CreateEventState.BONUS)
async def process_bonus(message: Message):
    if message.peer_id > 2000000000:
        return
    skip_words = ["пропустить", "нет", "нету", "-", "0"]
    text = message.text.lower().strip()
    bonus = None if text in skip_words else message.text.strip()

    state = await bot.state_dispenser.get(message.peer_id)
    # ДОБАВИЛИ or {}
    await bot.state_dispenser.set(message.peer_id, CreateEventState.CHAT_LINK, **(state.payload or {}), bonus=bonus)
    await message.answer("Ссылка на общий чат?\n\nОтправь ссылку (начиная с http) или напиши «Нет»:", keyboard=get_skip_keyboard())

# --- ШАГ 9: ССЫЛКА НА ЧАТ (ОПЦИОНАЛЬНО) ---
@bot.on.message(state=CreateEventState.CHAT_LINK)
async def process_chat_link(message: Message):
    if message.peer_id > 2000000000:
        return
    skip_words = ["пропустить", "нет", "нету", "-", "0"]
    text = message.text.lower().strip()

    if text in skip_words:
        chat_link = None
    else:
        chat_link = message.text.strip()
        if not chat_link.startswith("http"):
            await message.answer("Ссылка должна начинаться с http:// или https://.\nПопробуй снова или напиши «Нет»:")
            return

    state = await bot.state_dispenser.get(message.peer_id)
    p = state.payload or {}
    
    await bot.state_dispenser.set(message.peer_id, CreateEventState.CONFIRMATION, **p, chat_link=chat_link)

    # --- ЛОГИКА КРАСИВОГО ТЕКСТА ---
    
    # 1. Умное отображение количества
    max_vol = str(p.get('max_vol', '???')).lower()
    if max_vol == "все":
        vol_text = "👥 Нужны все!"
    else:
        vol_text = f"👥 Нужны {max_vol} человек"
        
    # 2. Опциональные поля (показываем только если есть)
    bonus_str = f"\n🎁 Бонусы: {p.get('bonus')}" if p.get('bonus') else ""
    chat_str = f"\n🔗 Чат: {chat_link}" if chat_link else ""

    # 3. Собираем красивый предпросмотр
    preview = (
        f"📌 {p.get('title', 'Без названия')}\n\n"
        f"📅 Дата: {p.get('date', '???')} с {p.get('time_start', '???')} до {p.get('time_end', '???')}\n"
        f"📍 Место: {p.get('location', '???')}\n"
        f"{vol_text}\n\n"
        f"📝 Описание:\n{p.get('description', '???')}"
        f"{bonus_str}{chat_str}\n\n"
        f"Всё верно?"
    )

    kb = (
        Keyboard(one_time=False, inline=False)
        .add(Text("✅ Опубликовать"), color=KeyboardButtonColor.POSITIVE)
        .add(Text("🔄 Заново"), color=KeyboardButtonColor.SECONDARY)
        .row().add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
        .get_json()
    )

    await message.answer(preview, keyboard=kb)


@bot.on.message(state=CreateEventState.CONFIRMATION, regex=r"(?i).*опубликовать.*")
async def process_publish(message: Message):
    try:
        user = get_user_by_vk_id(message.from_id)
        if not user:
            await message.answer("❌ Ошибка: тебя нет в базе. Напиши /start заново!")
            await bot.state_dispenser.delete(message.peer_id)
            return

        state = await bot.state_dispenser.get(message.peer_id)
        p = state.payload or {}

        # Парсим дату и время
        date_str = p.get("date")
        if len(date_str.split('.')) == 2:
            event_date = datetime.strptime(f"{date_str}.{datetime.now().year}", "%d.%m.%Y").date()
        else:
            event_date = datetime.strptime(date_str, "%d.%m.%Y").date()

        start_time_obj = datetime.strptime(p.get("time_start"), "%H:%M").time()
        end_time_obj = datetime.strptime(p.get("time_end"), "%H:%M").time()

        # Сохраняем в БД
        event = create_event(
            author_id=user.id,
            title=p.get("title"),
            max_volunteers=p.get("max_vol"),
            gender_required=p.get("gender"),
            date=event_date,
            start_time=start_time_obj,
            end_time=end_time_obj,
            location=p.get("location"),
            description=p.get("description"),
            bonus_info=p.get("bonus"),
            chat_link=p.get("chat_link")
        )

        if not event:
            await message.answer("❌ Не удалось сохранить мероприятие в БД.")
            return

        # Формируем сообщение
        vol_text = "👥 Нужны все!" if str(event.max_volunteers).lower() == "все" else f"👥 Нужны {event.max_volunteers} человек"
        
        chat_text = (
            f"📌 {event.title}\n\n"
            f"📅 Дата: {event.date.strftime('%d.%m')} с {event.start_time.strftime('%H:%M')} до {event.end_time.strftime('%H:%M')}\n"
            f"📍 Место: {event.location}\n"
            f"{vol_text}\n\n"
            f"📝 Описание:\n{event.description}"
        )
        if event.bonus_info: chat_text += f"\n\n🎁 Бонусы: {event.bonus_info}"
        if event.chat_link: chat_text += f"\n🔗 Чат: {event.chat_link}"

        # Твоя ссылка от ngrok (без слэша на конце) ДВЕ КНОПКИ: ОТКЛИК И СЧЕТЧИК
        NGROK_URL = "https://brought-porous-cheek.ngrok-free.dev"
        
                # Формируем ссылку
        app_link = f"https://vk.com/app54895625?event_id={event.id}"

        # ДВЕ КНОПКИ: ОТКЛИК И СПИСОК
        kb = (
            Keyboard(inline=True)
            .add(Callback("✅ Я пойду", payload={"cmd": "join_chat", "id": str(event.id)}), color=KeyboardButtonColor.POSITIVE)
            # ВОТ ЗДЕСЬ ИСПОЛЬЗУЕМ link, А НЕ url!
            .add(OpenLink(app_link, label=f"👥 Список (0/{event.max_volunteers})"), color=KeyboardButtonColor.SECONDARY)
        )

        # Отправляем в чат
        await bot.api.messages.send(
            peer_id=CHAT_ID,
            message=chat_text,
            keyboard=kb.get_json(),
            random_id=random.randint(1, 1000000)
        )

        await message.answer("✅ Мероприятие успешно опубликовано в рабочем чате!", keyboard=get_main_menu_keyboard())
        await bot.state_dispenser.delete(message.peer_id)

    except Exception as e:
        print(f"⚠️ КРИТИЧЕСКАЯ ОШИБКА ПРИ ПУБЛИКАЦИИ: {e}")
        await message.answer(f"❌ Ошибка при отправке: {e}", keyboard=get_main_menu_keyboard())

@bot.on.message(state=CreateEventState.CONFIRMATION, text=["🔄 Заново", "Заново"])
async def process_restart(message: Message):
    if message.peer_id > 2000000000:
        return
    await start_create(message)

@bot.on.message(state=CreateEventState.CONFIRMATION, text=["❌ Отмена", "Отмена"])
async def process_cancel(message: Message):
    if message.peer_id > 2000000000:
        return
    await cancel_create(message)


@bot.on.message(state=AnnouncementState.PREVIEW, text=["✅ Опубликовать"])
async def publish_announcement(message: Message):
    state = await bot.state_dispenser.get(message.peer_id)
    p = state.payload or {}
    title = p.get("title")
    text = p.get("text")
    photo = p.get("photo")
    
    # Убираем HTML-теги, делаем заголовок ярким с помощью эмодзи и КАПСА
    final_message = f"🔥 {title.upper()} 🔥\n\n{text}"
    
    try:
        await bot.api.messages.send(
            peer_id=CHAT_ID,
            message=final_message,
            attachment=photo,
            random_id=random.randint(1, 1000000)
        )
        await message.answer("✅ Объявление успешно опубликовано в чате!", keyboard=get_main_menu_keyboard())
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        await message.answer(f"❌ Ошибка при публикации: {e}", keyboard=get_main_menu_keyboard())
        
    await bot.state_dispenser.delete(message.peer_id)
@bot.on.message(state=AnnouncementState.PREVIEW, text=["❌ Отмена"])
async def cancel_announcement(message: Message):
    await bot.state_dispenser.delete(message.peer_id)
    await message.answer("❌ Создание объявления отменено.", keyboard=get_main_menu_keyboard())