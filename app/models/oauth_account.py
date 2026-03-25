import uuid
from datetime import datetime, UTC
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class OAuthAccount(Base):

    __tablename__ = "oauth_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    provider = Column(String, nullable=False)

    provider_user_id = Column(String, nullable=False)

    email = Column(String, nullable=True)

    email_verified = Column(Boolean, default=False)

    name = Column(String, nullable=True)

    picture = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )

    user = relationship("User", back_populates="oauth_accounts")
    
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_provider_user",
        ),
    )