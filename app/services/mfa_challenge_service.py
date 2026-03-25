import secrets
import json

from app.cache.redis_client import redis_client
from app.core.config import settings


class MFAChallengeService:

    def create_challenge(self, user_id: str):

        token = secrets.token_urlsafe(32)

        payload = {
            "user_id": str(user_id)
        }

        redis_client.setex(
            self._key(token),
            settings.MFA_CHALLENGE_TTL,
            json.dumps(payload)
        )
        
        redis_client.setex(self._attempt_key(token), 300, 0)
        return token

    def verify_challenge(self, token: str):

        raw = redis_client.get(self._key(token))

        if not raw:
            return None

        data = json.loads(raw)

        return data["user_id"]
    
    def delete_challenge(self, token: str):

        pipe = redis_client.pipeline()

        pipe.delete(self._key(token))
        pipe.delete(self._attempt_key(token))

        pipe.execute()

    def check_attempts(self, token: str):

        attempts = redis_client.get(self._attempt_key(token))

        if attempts and int(attempts) >= settings.MFA_MAX_ATTEMPTS:
            return False

        return True

    def increment_attempt(self, token: str):

        redis_client.incr(self._attempt_key(token))

        redis_client.expire(
            self._attempt_key(token),
            settings.MFA_CHALLENGE_TTL
        )

    

    def _key(self, token: str):

        return f"mfa_challenge:{token}"

    def _attempt_key(self, token: str):

        return f"mfa_attempts:{token}"