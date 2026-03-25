import secrets
import hashlib

from app.models.recovery_code import RecoveryCode
from app.repositories.recovery_code_repository import RecoveryCodeRepository


class RecoveryCodeService:

    def __init__(self, recovery_code_repo: RecoveryCodeRepository):
        self.recovery_code_repo = recovery_code_repo

    # -------------------------
    # Generate recovery codes
    # -------------------------

    def generate_codes(self, user_id):

        codes = []

        for _ in range(10):

            raw = secrets.token_hex(4).upper()

            formatted = f"{raw[:4]}-{raw[4:]}"

            hashed = self._hash(formatted)

            code = RecoveryCode(
                user_id=user_id,
                code_hash=hashed
            )

            self.recovery_code_repo.create(code)

            codes.append(formatted)

        return codes

    # -------------------------
    # Verify recovery code
    # -------------------------

    def verify_code(self, user_id, code):

        hashed = self._hash(code)

        recovery = self.recovery_code_repo.find_valid_code(user_id, hashed)

        if not recovery:
            return False

        self.recovery_code_repo.mark_used(recovery)

        return True

    def _hash(self, value):

        return hashlib.sha256(value.encode()).hexdigest()