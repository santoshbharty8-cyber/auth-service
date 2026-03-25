import logging
import sys
import json
from datetime import datetime, timezone

SERVICE_NAME = "auth-service"
LOG_VERSION = 1


class JsonFormatter(logging.Formatter):

    def format(self, record):

        log_record = {
            "log_version": LOG_VERSION,
            "service": SERVICE_NAME,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
        }

        # Optional structured fields
        optional_fields = [
            "event",
            "request_id",
            "user_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "client_ip",
            "endpoint",
            "identifier",
            "limit",
            "remaining",
            "window_ms",
        ]

        for field in optional_fields:
            value = getattr(record, field, None)
            if value is not None:
                log_record[field] = value

        # Include exception details if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def setup_logging():

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # remove default handlers (uvicorn adds some)
    root.handlers.clear()
    root.addHandler(handler)

    # Optional: reduce uvicorn noise
    logging.getLogger("uvicorn.access").disabled = True