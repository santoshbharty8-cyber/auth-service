import uuid
from datetime import datetime, UTC
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class WebAuthnCredential(Base):

    __tablename__ = "webauthn_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), nullable=False)

    credential_id = Column(String, unique=True, nullable=False)

    public_key = Column(String, nullable=False)

    sign_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))