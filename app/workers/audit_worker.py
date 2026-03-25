import json
import time
from sqlalchemy.orm import Session

from app.cache.redis_client import redis_client
from app.core.database import SessionLocal
from app.models.audit_log import AuditLog

QUEUE_NAME = "audit:queue"
PROCESSING_QUEUE = "audit:processing"


def save_to_db(event_dict):
    db: Session = SessionLocal()

    try:
        log = AuditLog(
            user_id=event_dict.get("user_id"),
            event_type=event_dict["event_type"],
            event_status=event_dict["event_status"],
            ip_address=event_dict.get("ip_address"),
            user_agent=event_dict.get("user_agent"),
            metadata=event_dict.get("metadata"),
        )

        db.add(log)
        db.commit()
    finally:
        db.close()


def start_worker():
    print("🚀 Audit Worker Started...")

    while True:
        try:
            # Move event safely to processing queue
            event_json = redis_client.brpoplpush(
                QUEUE_NAME,
                PROCESSING_QUEUE,
                timeout=5
            )

            if not event_json:
                continue

            event = json.loads(event_json)

            save_to_db(event)

            # Remove from processing after success
            redis_client.lrem(PROCESSING_QUEUE, 1, event_json)

        except Exception as e:
            print("Worker error:", e)
            time.sleep(2)


if __name__ == "__main__":
    start_worker()