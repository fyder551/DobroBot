import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Загружаем переменные из .env, чтобы os.getenv их видел
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # 1. Заменяем старый протокол, если он есть
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # 2. ВАЖНО: Говорим SQLAlchemy использовать psycopg (3 версию), а не psycopg2
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
        
    engine = create_engine(DATABASE_URL)
    print("✅ Бот подключен к облачной базе PostgreSQL (psycopg 3)")
else:
    # Для локальной разработки (SQLite)
    # ... (остальной код для SQLite оставляем без изменений) ...
    # Для локальной разработки (SQLite)
    DATABASE_URL = "sqlite:///v2_bot.db"
    engine = create_engine(
        DATABASE_URL, 
        echo=False,
        connect_args={"check_same_thread": False, "timeout": 15}
    )
    print("⚠️ Бот использует локальную базу SQLite")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db():
    from app.database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

def get_session():
    return SessionLocal()