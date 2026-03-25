import secrets
import hashlib
import base64
import json




class OAuthHelper:

    PREFIX = "oauth:state:"
    TTL = 600

    @staticmethod
    def generate_state():
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_pkce():

        code_verifier = secrets.token_urlsafe(64)

        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")

        return code_verifier, challenge

    @staticmethod
    def store_state(redis_client, state, data):

        redis_client.setex(
            f"{OAuthHelper.PREFIX}{state}",
            OAuthHelper.TTL,
            json.dumps(data)
        )

    @staticmethod
    def consume_state(redis_client, state):

        key = f"{OAuthHelper.PREFIX}{state}"

        data = redis_client.get(key)

        if not data:
            return None

        redis_client.delete(key)

        return json.loads(data)