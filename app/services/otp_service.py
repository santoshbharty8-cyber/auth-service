import json
import secrets
import hashlib

from app.cache.redis_client import redis_client
from app.core.config import settings


class OTPService:

    # -----------------------------
    # Generate OTP
    # -----------------------------
    def generate_otp(self, identifier: str, fingerprint: str, ip: str):

        otp = str(secrets.randbelow(900000) + 100000)

        payload = {
            "otp": self._hash(otp),
            "fingerprint": fingerprint,
            "ip": ip
        }

        redis_client.setex(
            self._otp_key(identifier),
            settings.OTP_EXPIRE_SECONDS,
            json.dumps(payload)
        )

        redis_client.setex(
            self._attempts_key(identifier),
            settings.OTP_EXPIRE_SECONDS,
            0
        )

        return otp

    # -----------------------------
    # Verify OTP
    # -----------------------------
    def verify_otp(self, identifier: str, otp: str, fingerprint: str, ip: str):

        key = self._otp_key(identifier)

        raw = redis_client.get(key)

        if not raw:
            return False

        data = json.loads(raw)

        # Device fingerprint check
        if data["fingerprint"] != fingerprint:
            return False

        # IP binding
        if data["ip"] != ip:
            print("IP mismatch during OTP verification")

        attempts_key = self._attempts_key(identifier)

        attempts = redis_client.get(attempts_key)

        if attempts and int(attempts) >= settings.OTP_MAX_ATTEMPTS:
            return False

        if data["otp"] != self._hash(otp):

            redis_client.incr(attempts_key)

            return False

        redis_client.delete(key)
        redis_client.delete(attempts_key)

        return True

    # -----------------------------
    # Rate limit OTP requests
    # -----------------------------
    def rate_limit(self, identifier: str):

        key = self._rate_key(identifier)

        count = redis_client.incr(key)

        if count == 1:
            redis_client.expire(
                key,
                settings.OTP_RATE_LIMIT_WINDOW
            )

        if count > settings.OTP_RATE_LIMIT:
            return False

        return True

    # -----------------------------
    # Helpers
    # -----------------------------

    def _hash(self, value: str):
        return hashlib.sha256(value.encode()).hexdigest()

    def _otp_key(self, identifier: str):
        return f"otp:{identifier}"

    def _attempts_key(self, identifier: str):
        return f"otp_attempts:{identifier}"

    def _rate_key(self, identifier: str):
        return f"otp_rate:{identifier}"