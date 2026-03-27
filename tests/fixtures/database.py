from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


def get_test_db():
    # Create tables ONCE
    Base.metadata.create_all(bind=engine)

    connection = engine.connect()
    transaction = connection.begin()

    db = TestingSessionLocal(bind=connection)

    try:
        yield db
    finally:
        db.close()
        transaction.rollback()   # 🔥 key point
        connection.close()