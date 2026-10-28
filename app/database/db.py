from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///bot.db"

# Для SQLite используем check_same_thread=False (чтобы бот работал асинхронно)
# и timeout=15 (чтобы при одновременной записи бот ждал, а не падал с ошибкой)
engine = create_engine(
    DATABASE_URL, echo=False, connect_args={"check_same_thread": False, "timeout": 15}
)


# Включаем режим WAL (Write-Ahead Logging) для SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db():
    """Создаёт все таблицы, если их ещё нет."""
    from app.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_session():
    """Возвращает новую сессию для работы с БД."""
    return SessionLocal()
