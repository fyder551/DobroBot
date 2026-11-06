from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# База данных будет создана в корне папки v2
DATABASE_URL = "sqlite:///v2_bot.db"

engine = create_engine(
    DATABASE_URL, 
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 15}
)

# Включаем режим WAL (чтобы не было блокировок при одновременных запросах)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db():
    """Создает все таблицы, если их еще нет"""
    from app.database import models  # Импортируем модели, чтобы SQLAlchemy их увидел
    Base.metadata.create_all(bind=engine)

def get_session():
    """Возвращает новую сессию для работы с БД"""
    return SessionLocal()