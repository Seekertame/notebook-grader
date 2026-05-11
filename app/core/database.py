import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv("NBGRADER_DATABASE_URL")
if DATABASE_URL is None:
    import warnings
    warnings.warn(
        "Переменная окружения NBGRADER_DATABASE_URL не установлена. "
        "Используется значение по умолчанию для локальной разработки.",
        RuntimeWarning,
    )
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/grader_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
