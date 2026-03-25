import json
from datetime import datetime, UTC
from app.cache.redis_client import redis_client


class AuditService:

    QUEUE_NAME = "audit:queue"
    PROCESSING_QUEUE = "audit:processing"

    def enqueue_event(
        self,
        event_type: str,
        event_status: str,
        user_id=None,
        ip_address=None,
        user_agent=None,
        metadata=None,
    ):
        event = {
            "event_type": event_type,
            "event_status": event_status,
            "user_id": str(user_id) if user_id else None,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata,
            "created_at": datetime.now(UTC).isoformat(),
        }

        redis_client.rpush(self.QUEUE_NAME, json.dumps(event))