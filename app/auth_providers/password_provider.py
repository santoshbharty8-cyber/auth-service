from app.auth_providers.base import BaseAuthProvider
from app.repositories.user_repository import UserRepository
from app.security.password import verify_password


class PasswordAuthProvider(BaseAuthProvider):

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def authenticate(self, data: dict):

        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return None

        user = self.user_repo.find_by_email(email)

        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user