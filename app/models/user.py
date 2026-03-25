import uuid
from datetime import datetime, UTC
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.associations import user_roles
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=True)
    status = Column(String, default="ACTIVE")
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    token_version = Column(Integer, default=0, nullable=False)
    phone_number = Column(String, unique=True, nullable=True)
    phone_verified = Column(Boolean, default=False)
    
    roles = relationship(
        "Role",
        secondary=user_roles,
        backref="users"
    )
    
    oauth_accounts = relationship(
    "OAuthAccount",
    back_populates="user",
    cascade="all, delete-orphan"
)
