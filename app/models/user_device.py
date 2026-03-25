import uuid
from datetime import datetime, UTC
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class UserDevice(Base):

    __tablename__ = "user_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), nullable=False)

    fingerprint = Column(String, nullable=False)

    user_agent = Column(String)

    ip_address = Column(String)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
