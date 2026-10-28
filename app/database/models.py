from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Date,
    Time,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.database.db import Base


class User(Base):
    """Пользователь бота: волонтёр, организатор или админ."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vk_id = Column(Integer, unique=True, nullable=False, index=True)
    vk_first_name = Column(String(100), nullable=True)
    full_name = Column(String(150), nullable=True)
    gender = Column(String(10), nullable=True)  # 'male' / 'female'
    role = Column(String(20), default="volunteer", nullable=False, index=True)
    university = Column(String(100), default="ВГУИТ", nullable=False)
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False, index=True)
    ban_reason = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Связи
    events = relationship(
        "Event", back_populates="organizer", foreign_keys="Event.organizer_id"
    )
    responses = relationship("Response", back_populates="user")
    previous_role = Column(String(20), nullable=True)
    previous_role_expires_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User vk_id={self.vk_id} name={self.full_name} role={self.role}>"


class Event(Base):
    """Волонтёрское мероприятие."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    date = Column(Date, nullable=False, index=True)
    time = Column(Time, nullable=False)

    end_time = Column(Time, nullable=True)  # <-- Время окончания
    chat_link = Column(String(300), nullable=True)  # <-- Ссылка на чат/форму
    bonus_info = Column(String(300), nullable=True)  # <-- Плюшки

    location = Column(String(200), nullable=False)
    contacts = Column(String(200), nullable=False)  # pending / approved / rejected
    rejection_reason = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    max_volunteers = Column(String(50), nullable=True)  # "20" или "Все"
    gender_required = Column(
        String(20), default="all", nullable=True
    )  # "all", "male", "female"
    status = Column(String(20), default="pending", nullable=False, index=True)

    # Связи
    organizer = relationship(
        "User", back_populates="events", foreign_keys=[organizer_id]
    )
    responses = relationship("Response", back_populates="event")

    def __repr__(self):
        return f"<Event id={self.id} title={self.title} status={self.status}>"


class Response(Base):
    """Отклик волонтёра на мероприятие."""

    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(
        String(20), default="confirmed", nullable=False
    )  # confirmed / cancelled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    attended = Column(Boolean, default=False, nullable=False)

    # Связи
    event = relationship("Event", back_populates="responses")
    user = relationship("User", back_populates="responses")

    def __repr__(self):
        return f"<Response event_id={self.event_id} user_id={self.user_id} status={self.status}>"
