"""Функции для работы с базой данных (CRUD)."""

from typing import Optional


from app.database.db import get_session
from datetime import date
from app.database.models import User, Event
from app.database.models import Response
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta


def get_user_by_vk_id(vk_id: int) -> Optional[User]:
    """Находит пользователя по его VK ID."""
    session = get_session()
    try:
        return session.query(User).filter_by(vk_id=vk_id).first()
    finally:
        session.close()


def create_user(
    vk_id: int,
    vk_first_name: str,
    gender: str,
    full_name: str,
) -> User:
    """Создаёт нового пользователя."""
    session = get_session()
    try:
        user = User(
            vk_id=vk_id,
            vk_first_name=vk_first_name,
            gender=gender,
            full_name=full_name,
            role="volunteer",
            university="ВГУИТ",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


def update_user_gender(vk_id: int, gender: str) -> None:
    """Обновляет пол пользователя."""
    session = get_session()
    try:
        user = session.query(User).filter_by(vk_id=vk_id).first()
        if user:
            user.gender = gender
            session.commit()
    finally:
        session.close()


def update_user_full_name(vk_id: int, full_name: str) -> None:
    """Обновляет ФИО пользователя."""
    session = get_session()
    try:
        user = session.query(User).filter_by(vk_id=vk_id).first()
        if user:
            user.full_name = full_name
            session.commit()
    finally:
        session.close()


def change_role(vk_id: int, new_role: str) -> None:
    """Меняет роль пользователя без сохранения previous_role (для повышения)."""
    session = get_session()
    try:
        user = session.query(User).filter_by(vk_id=vk_id).first()
        if user:
            user.role = new_role
            user.previous_role = None
            user.previous_role_expires_at = None
            session.commit()
    finally:
        session.close()


def downgrade_role(vk_id: int, new_role: str) -> None:
    """Понижает роль, сохраняя previous_role с окном на 2 минуты."""
    session = get_session()
    try:
        user = session.query(User).filter_by(vk_id=vk_id).first()
        if user:
            user.previous_role = user.role
            user.previous_role_expires_at = datetime.utcnow() + timedelta(minutes=2)
            user.role = new_role
            session.commit()
    finally:
        session.close()


def can_return_to_previous(vk_id: int) -> bool:
    """Проверяет, можно ли вернуться в previous_role без кода."""
    session = get_session()
    try:
        user = session.query(User).filter_by(vk_id=vk_id).first()
        if not user or not user.previous_role or not user.previous_role_expires_at:
            return False
        return datetime.utcnow() < user.previous_role_expires_at
    finally:
        session.close()


def create_event(
    organizer_id: int,
    title: str,
    date,
    time_,
    location: str,
    description: str,
    max_volunteers: str,
    gender_required: str,
    contacts: str,
    end_time=None,
    chat_link=None,
    bonus_info=None,
) -> Event:
    """Создаёт новое мероприятие со статусом pending."""
    session = get_session()
    try:
        event = Event(
            organizer_id=organizer_id,
            title=title,
            date=date,
            time=time_,
            location=location,
            description=description,
            max_volunteers=max_volunteers,
            gender_required=gender_required,
            contacts=contacts,
            status="pending",
            end_time=end_time,
            chat_link=chat_link,
            bonus_info=bonus_info,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event
    finally:
        session.close()


def get_event_by_id(event_id: int) -> Event | None:
    """Находит мероприятие по ID."""
    session = get_session()
    try:
        return session.query(Event).filter_by(id=event_id).first()
    finally:
        session.close()


def approve_event(event_id: int) -> None:
    """Одобряет мероприятие."""
    session = get_session()
    try:
        event = session.query(Event).filter_by(id=event_id).first()
        if event:
            event.status = "approved"
            session.commit()
    finally:
        session.close()


def reject_event(event_id: int, reason: str = "") -> None:
    """Отклоняет мероприятие."""
    session = get_session()
    try:
        event = session.query(Event).filter_by(id=event_id).first()
        if event:
            event.status = "rejected"
            event.rejection_reason = reason
            session.commit()
    finally:
        session.close()


def get_approved_events():
    """Возвращает одобренные мероприятия, которые еще не прошли."""
    session = get_session()
    try:
        return (
            session.query(Event)
            .filter(Event.status == "approved", Event.date >= date.today())
            .order_by(Event.date, Event.time)
            .all()
        )
    finally:
        session.close()


def get_user_events(user_id: int):
    """Возвращает все мероприятия, созданные пользователем."""
    session = get_session()
    try:
        return (
            session.query(Event)
            .filter_by(organizer_id=user_id)
            .order_by(Event.created_at.desc())
            .all()
        )
    finally:
        session.close()


def update_user_notifications(vk_id: int, enabled: bool) -> None:
    session = get_session()
    try:
        user = session.query(User).filter_by(vk_id=vk_id).first()
        if user:
            user.notifications_enabled = enabled
            session.commit()
    finally:
        session.close()


def create_response(event_id: int, user_id: int) -> Response | None:
    """Создаёт отклик на мероприятие. Если уже есть — возвращает None."""
    session = get_session()
    try:
        # Проверяем, нет ли уже отклика
        existing = (
            session.query(Response)
            .filter_by(event_id=event_id, user_id=user_id)
            .first()
        )
        if existing:
            return None

        response = Response(event_id=event_id, user_id=user_id, status="confirmed")
        session.add(response)
        session.commit()
        session.refresh(response)
        return response
    finally:
        session.close()


def get_event_by_title(title: str):
    """Ищет мероприятие по точному названию (для команды /join)."""
    session = get_session()
    try:
        return session.query(Event).filter(Event.title.ilike(f"%{title}%")).first()
    finally:
        session.close()


def get_organizer_events(organizer_id: int):
    """Возвращает все мероприятия, созданные организатором."""
    session = get_session()
    try:
        return (
            session.query(Event)
            .filter_by(organizer_id=organizer_id)
            .order_by(Event.date.desc())
            .all()
        )
    finally:
        session.close()


def get_event_responses(event_id: int):
    """Возвращает список откликнувшихся на мероприятие."""
    session = get_session()
    try:
        return (
            session.query(Response)
            .filter_by(event_id=event_id, status="confirmed")
            .all()
        )
    finally:
        session.close()


def get_user_responses(user_id: int):
    """Возвращает список откликов пользователя с подгруженными мероприятиями."""
    session = get_session()
    try:
        # joinedload загружает связанное мероприятие сразу, решая проблему с закрытой сессией
        return (
            session.query(Response)
            .options(joinedload(Response.event))
            .filter_by(user_id=user_id, status="confirmed")
            .order_by(Response.created_at.desc())
            .all()
        )
    finally:
        session.close()


def mark_attendance(response_id: int, attended: bool = True):
    """Отмечает, пришел волонтер или нет."""
    session = get_session()
    try:
        response = session.query(Response).filter_by(id=response_id).first()
        if response:
            response.attended = attended
            session.commit()
    finally:
        session.close()


def get_event_responses_with_details(event_id: int):
    """Возвращает список откликов на мероприятие (для организатора)."""
    session = get_session()
    try:
        return (
            session.query(Response)
            .options(joinedload(Response.user))
            .filter_by(event_id=event_id, status="confirmed")
            .all()
        )
    finally:
        session.close()
