import httpx
import uuid

from google.oauth2 import id_token
from google.auth.transport import requests

from fastapi import HTTPException, status


from app.repositories.user_repository import UserRepository
from app.repositories.oauth_repository import OAuthRepository
from app.models import User
from app.models.oauth_account import OAuthAccount
from app.core.config import settings


class GoogleOAuthProvider:

    def __init__(self, user_repo: UserRepository, oauth_repo: OAuthRepository):

        self.user_repo = user_repo
        self.oauth_repo = oauth_repo

    def authenticate(self, code: str, code_verifier: str, flow: str):
        
        token_data = self.exchange_code_for_token(code, code_verifier)

        payload = id_token.verify_oauth2_token(
            token_data["id_token"],
            requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )

        provider_user_id = payload["sub"]
        email = payload["email"]
        
        if not payload.get("email_verified"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google email not verified"
            )
        if flow == "link":
            pass

        oauth_account = self.oauth_repo.find_by_provider_user_id(
            "google",
            provider_user_id
        )

        if oauth_account:
            return oauth_account.user

        user = self.user_repo.find_by_email(email)
        
        # user exists but OAuth not linked
        if user:
            return {
                "link_required": True,
                "email": email,
                "provider_user_id": provider_user_id,
                "payload": payload
            }

        user = User(
            email=email,
            password_hash=None,   # OAuth users have no password
            status="ACTIVE"
        )

        user = self.user_repo.create(user)

        oauth_account = OAuthAccount(
            id=uuid.uuid4(),
            user_id=user.id,
            provider="google",
            provider_user_id=provider_user_id,
            email=email,
            email_verified=payload.get("email_verified"),
            name=payload.get("name"),
            picture=payload.get("picture"),
        )

        self.oauth_repo.create(oauth_account)

        return user

    def exchange_code_for_token(self, code, code_verifier):

        with httpx.Client() as client:

            response = client.post(
                settings.GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                    "code_verifier": code_verifier
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OAuth token exchange failed"
            )

        return response.json()
    
    def verify_identity(self, id_token_value):

        payload = id_token.verify_oauth2_token(
            id_token_value,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )

        if not payload.get("email_verified"):
            raise Exception("Google email not verified")

        return payload