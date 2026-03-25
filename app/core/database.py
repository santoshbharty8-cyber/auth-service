from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import Session
from typing import Generator

from app.core.config import settings


# -------------------------
# SQLAlchemy Engine
# -------------------------
engine = create_engine(
    settings.database_url,
    echo=settings.DEBUG,          # show SQL in development
    pool_pre_ping=True,           # detect stale connections
    pool_size=10,                 # production-safe defaults
    max_overflow=20,
    future=True
)


# -------------------------
# Session Factory
# -------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)


# -------------------------
# Base Model
# -------------------------
Base = declarative_base()


# -------------------------
# DB Dependency (FastAPI)
# -------------------------
def get_db() -> Generator[Session, None, None]:

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()