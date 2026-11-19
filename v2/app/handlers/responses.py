import io
import random

import aiohttp
from vkbottle import GroupEventType, Keyboard, Callback, KeyboardButtonColor
from vkbottle.bot import MessageEvent
from app.bot_instance import bot
from app.config import GROUP_ID
from app.database.crud import (
    get_user_by_vk_id,
    get_event_by_id,
    create_response,
    get_event_responses_count,
    get_event_responses,
)
from app.logger import logger


@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "join_chat"}
)
async def join_chat_callback(event: MessageEvent):
    try:
        user = get_user_by_vk_id(event.user_id)

        # --- АВТОРЕГИСТРАЦИЯ ---
        if not user:
            try:
                users_info = await bot.api.users.get(user_ids=event.user_id)
                if users_info:
                    vk_user = users_info[0]
                    gender = (
                        "male"
                        if vk_user.sex == 2
                        else ("female" if vk_user.sex == 1 else "unknown")
                    )
                    from app.database.crud import get_or_create_user

                    user = get_or_create_user(
                        vk_id=event.user_id,
                        first_name=vk_user.first_name,
                        last_name=vk_user.last_name or "",
                        gender=gender,
                    )
            except Exception as e:
                logger.error(f"Ошибка авторегистрации: {e}")
                return

        event_id = int(event.payload["id"])
        event_db = get_event_by_id(event_id)
        if not event_db:
            return

        # Пытаемся записать в БД
        response = create_response(event_id=event_db.id, user_id=user.id)

        # Считаем актуальное количество записавшихся (в любом случае)
        count = get_event_responses_count(event_id)

        # Показываем окошко пользователю
        if not response:
            await event.show_snackbar(f"ℹ️ Ты уже записался! Всего: {count}")
        else:
            await event.show_snackbar(f"✅ Успешно! Всего: {count}")

        # --- ОБНОВЛЯЕМ СЧЁТЧИК ---
        try:
            if str(event_db.max_volunteers).lower() == "все":
                btn_text = f"👥 Список ({count}/все)"
            else:
                btn_text = f"👥 Список ({count}/{event_db.max_volunteers})"

            chat_text = (
                f"📌 {event_db.title}\n\n"
                f"📅 Дата: {event_db.date.strftime('%d.%m')} с {event_db.start_time.strftime('%H:%M')} до {event_db.end_time.strftime('%H:%M')}\n"
                f"📍 Место: {event_db.location}\n"
                f"📝 Описание:\n{event_db.description}"
            )
            if event_db.bonus_info:
                chat_text += f"\n\n🎁 Бонусы: {event_db.bonus_info}"
            if event_db.chat_link:
                chat_text += f"\n🔗 Чат: {event_db.chat_link}"

            kb = (
                Keyboard(inline=True)
                .add(
                    Callback(
                        "✅ Я пойду",
                        payload={"cmd": "join_chat", "id": str(event_db.id)},
                    ),
                    color=KeyboardButtonColor.POSITIVE,
                )
                .add(
                    Callback(
                        btn_text, payload={"cmd": "view_list", "id": str(event_db.id)}
                    ),
                    color=KeyboardButtonColor.SECONDARY,
                )
            )

            await bot.api.messages.edit(
                peer_id=event.peer_id,
                conversation_message_id=event.conversation_message_id,
                group_id=GROUP_ID,
                message=chat_text,
                keyboard=kb.get_json(),
            )
            logger.info(f"✅ Кнопка обновлена. Записалось: {count}")

        except Exception as e:
            logger.error(f"❌ ВК НЕ ДАЛ ОБНОВИТЬ КНОПКУ: {e}")

    except Exception as e:
        logger.error(f"Критическая ошибка в join_chat: {e}")


@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, payload_contains={"cmd": "view_list"}
)
async def view_list_callback(event: MessageEvent):
    try:
        event_id = int(event.payload["id"])
        event_db = get_event_by_id(event_id)
        if not event_db:
            return

        user = get_user_by_vk_id(event.user_id)
        count = get_event_responses_count(event_id)

        # ВОЛОНТЁР: просто показываем счётчик
        if not user or event_db.author_id != user.id:
            await event.show_snackbar(
                f"👥 Записались: {count} из {event_db.max_volunteers}"
            )
            return

        # СОЗДАТЕЛЬ: собираем список в txt-файл
        responses = get_event_responses(event_id)
        if not responses:
            await event.show_snackbar("Пока никто не записался 😢")
            return

        lines = [
            f"Список участников: {event_db.title}",
            f"Дата: {event_db.date.strftime('%d.%m.%Y')} {event_db.start_time.strftime('%H:%M')}-{event_db.end_time.strftime('%H:%M')}",
            f"Место: {event_db.location}",
            f"Всего записалось: {len(responses)}",
            "",
        ]
        for i, r in enumerate(responses, 1):
            if r.user:
                lines.append(
                    f"{i}. {r.user.first_name} {r.user.last_name or ''} — vk.com/id{r.user.vk_id}"
                )

        content = "\n".join(lines).encode("utf-8")

        # Загружаем файл как документ и отправляем в личку создателю
        upload_url = (
            await bot.api.docs.get_messages_upload_server(
                peer_id=event.user_id, type="doc"
            )
        ).upload_url

        async with aiohttp.ClientSession() as http:
            form = aiohttp.FormData()
            form.add_field(
                "file",
                io.BytesIO(content),
                filename=f"event_{event_db.id}_list.txt",
                content_type="text/plain",
            )
            async with http.post(upload_url, data=form) as resp:
                data = await resp.json()

        saved = await bot.api.docs.save(
            file=data["file"], title=f"Список — {event_db.title}"
        )
        attachment = f"doc{saved.doc.owner_id}_{saved.doc.id}"

        await bot.api.messages.send(
            peer_id=event.user_id,
            message=f"📄 Список на «{event_db.title}». Записалось: {len(responses)}",
            attachment=attachment,
            random_id=random.randint(1, 10**6),
        )
        await event.show_snackbar("📄 Список отправил тебе в личку!")

    except Exception as e:
        logger.error(f"Ошибка при выводе списка: {e}")
        try:
            await event.show_snackbar("❌ Ошибка при загрузке списка")
        except Exception:
            pass
