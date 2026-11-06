from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Time, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vk_id = Column(Integer, unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    gender = Column(String(10), nullable=True) # 'male' / 'female'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    events = relationship("Event", back_populates="author")
    responses = relationship("Response", back_populates="user")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    title = Column(String(200), nullable=False)
    max_volunteers = Column(String(50), nullable=False) # "10" или "Все"
    gender_required = Column(String(20), nullable=False) # "male", "female", "all"
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    location = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Необязательные поля
    bonus_info = Column(String(300), nullable=True)
    chat_link = Column(String(300), nullable=True)
    
    # Для работы онлайн-счетчика в чате
    vk_post_cmid = Column(Integer, nullable=True) 
    vk_post_id = Column(Integer, nullable=True)
    vk_post_random_id = Column(Integer, nullable=True) 
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    author = relationship("User", back_populates="events")
    responses = relationship("Response", back_populates="event")


class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    attended = Column(Boolean, default=False, nullable=False) # Пришел или нет
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    event = relationship("Event", back_populates="responses")
    user = relationship("User", back_populates="responses")