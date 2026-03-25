from app.auth_providers.base import BaseAuthProvider
from app.repositories.user_repository import UserRepository
from app.services.otp_service import OTPService


class OTPAuthProvider(BaseAuthProvider):

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        self.otp_service = OTPService()

    def authenticate(self, data: dict):

        email = data.get("email")
        otp = data.get("otp")
        fingerprint = data.get("fingerprint")
        ip = data.get("ip")
        identifier = f"email:{email}"

        user = self.user_repo.find_by_email(email)

        if not user:
            return None

        valid = self.otp_service.verify_otp(identifier, otp, fingerprint, ip)

        if not valid:
            return None

        return user