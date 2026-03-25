import uuid
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), nullable=True)

    event_type = Column(String, nullable=False)
    event_status = Column(String, nullable=False)  # SUCCESS / FAILURE

    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    meta_info = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())