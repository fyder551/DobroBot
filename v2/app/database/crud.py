from datetime import datetime
from typing import Optional
from sqlalchemy.orm import joinedload

from app.database.db import get_session
from app.database.models import User, Event, Response


# ==================== ПОЛЬЗОВАТЕЛИ ====================

def get_user_by_vk_id(vk_id: int) -> Optional[User]:
    """Ищет пользователя по его VK ID."""
    session = get_session()
    try:
        return session.query(User).filter_by(vk_id=vk_id).first()
    finally:
        session.close()


def get_or_create_user(vk_id: int, first_name: str, gender: str) -> User:
    """Возвращает пользователя из БД или создает нового, если его нет."""
    session = get_session()
    try:
        user = session.query(User).filter_by(vk_id=vk_id).first()
        if not user:
            user = User(
                vk_id=vk_id,
                first_name=first_name,
                gender=gender
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        return user
    finally:
        session.close()


# ==================== МЕРОПРИЯТИЯ ====================

def create_event(
    author_id: int,
    title: str,
    max_volunteers: str,
    gender_required: str,
    date,
    start_time,
    end_time,
    location: str,
    description: str,
    bonus_info: Optional[str] = None,
    chat_link: Optional[str] = None,
) -> Event:
    """Создает новое мероприятие в БД."""
    session = get_session()
    try:
        event = Event(
            author_id=author_id,
            title=title,
            max_volunteers=max_volunteers,
            gender_required=gender_required,
            date=date,
            start_time=start_time,
            end_time=end_time,
            location=location,
            description=description,
            bonus_info=bonus_info,
            chat_link=chat_link,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event
    finally:
        session.close()


def get_event_by_id(event_id: int) -> Optional[Event]:
    """Находит мероприятие по его ID."""
    session = get_session()
    try:
        return session.query(Event).filter_by(id=event_id).first()
    finally:
        session.close()


def update_event_cmid(event_id: int, cmid: int) -> None:
    """Сохраняет ID сообщения в чате (для онлайн-счетчика)."""
    session = get_session()
    try:
        event = session.query(Event).filter_by(id=event_id).first()
        if event:
            event.vk_post_cmid = cmid
            session.commit()
    finally:
        session.close()


# ==================== ОТКЛИКИ ====================

def create_response(event_id: int, user_id: int) -> Optional[Response]:
    """Создает отклик на мероприятие. Если уже есть — возвращает None."""
    session = get_session()
    try:
        # Проверяем, не записан ли уже
        existing = session.query(Response).filter_by(event_id=event_id, user_id=user_id).first()
        if existing:
            return None
        
        response = Response(event_id=event_id, user_id=user_id, attended=False)
        session.add(response)
        session.commit()
        session.refresh(response)
        return response
    finally:
        session.close()


def get_event_responses_count(event_id: int) -> int:
    """Возвращает количество записавшихся на мероприятие."""
    session = get_session()
    try:
        return session.query(Response).filter_by(event_id=event_id).count()
    finally:
        session.close()


def get_event_responses(event_id: int):
    """Возвращает список откликов с подгруженными данными пользователей."""
    session = get_session()
    try:
        return session.query(Response).options(joinedload(Response.user)).filter_by(event_id=event_id).all()
    finally:
        session.close()