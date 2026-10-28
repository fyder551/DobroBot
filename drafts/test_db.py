"""Тестовый скрипт: проверяем, что БД создаётся и модели работают."""
import os
import sys

# Добавляем корень проекта в путь, чтобы можно было импортировать app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date, time

from app.database.db import init_db, get_session
from app.database.models import User, Event, Response


def main():
    print("🛠️  Инициализация БД...")
    init_db()
    print("✅ Таблицы созданы (или уже существовали).")

    session = get_session()

    # Проверяем, есть ли уже тестовый пользователь
    test_vk_id = 999999999
    existing = session.query(User).filter_by(vk_id=test_vk_id).first()

    if existing:
        print(f"ℹ️  Тестовый пользователь уже есть: {existing}")
    else:
        # Создаём тестового пользователя
        user = User(
            vk_id=test_vk_id,
            vk_first_name="Тест",
            full_name="Иванов Иван Иванович",
            gender="male",
            role="organizer",
            university="ВГУИТ",
        )
        session.add(user)
        session.commit()
        print(f"✅ Создан пользователь: {user}")

        # Создаём мероприятие
        event = Event(
            organizer_id=user.id,
            title="Субботник в парке",
            description="Убираем мусор, сажаем деревья.",
            date=date(2026, 10, 25),
            time=time(10, 0),
            location="Парк Динамо, главный вход",
            contacts="@ivan_curator",
            status="approved",
        )
        session.add(event)
        session.commit()
        print(f"✅ Создано мероприятие: {event}")

        # Создаём отклик
        response = Response(event_id=event.id, user_id=user.id, status="confirmed")
        session.add(response)
        session.commit()
        print(f"✅ Создан отклик: {response}")

    # Проверяем, что всё читается
    print("\n📊 Содержимое БД:")
    users = session.query(User).all()
    events = session.query(Event).all()
    responses = session.query(Response).all()
    print(f"   Пользователей: {len(users)}")
    print(f"   Мероприятий: {len(events)}")
    print(f"   Откликов: {len(responses)}")

    session.close()
    print("\n🎉 Всё работает!")


if __name__ == "__main__":
    main()

    # Проверяем новые функции
    from app.database.crud import create_event, get_approved_events
    from datetime import date, time
    
    # Создаём одобренное мероприятие
    new_event = create_event(
        organizer_id=1,
        title="Тестовое мероприятие 2",
        date=date(2026, 11, 1),
        time_=time(15, 0),
        location="Актовый зал",
        description="Тестовое описание",
        contacts="@test",
    )
    # Одобряем
    from app.database.crud import approve_event
    approve_event(new_event.id)
    
    approved = get_approved_events()
    print(f"✅ Одобренных мероприятий: {len(approved)}")