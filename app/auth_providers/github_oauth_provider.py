import httpx
import uuid

from fastapi import HTTPException
from app.core.config import settings
from app.repositories.user_repository import UserRepository
from app.repositories.oauth_repository import OAuthRepository
from app.models import User
from app.models.oauth_account import OAuthAccount
from app.utils.oauth_config import get_oauth_redirect_uri


class GitHubOAuthProvider:

    def __init__(self, user_repo: UserRepository, oauth_repo: OAuthRepository):
        self.user_repo = user_repo
        self.oauth_repo = oauth_repo

    async def authenticate(self, code: str):

        pass
    
    async def exchange_code(self, code, code_verifier):
        
        redirect_uri = get_oauth_redirect_uri("github")

        async with httpx.AsyncClient() as client:

            resp = await client.post(
                settings.GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.AUTH_GITHUB_CLIENT_ID,
                    "client_secret": settings.AUTH_GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier
                }
            )

        return resp.json()["access_token"]
    
    async def fetch_user(self, access_token):

        async with httpx.AsyncClient() as client:

            resp = await client.get(
                settings.GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
            )

        return resp.json()
    
    async def fetch_email(self, access_token):

        async with httpx.AsyncClient() as client:

            resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
            )

        emails = resp.json()

        primary = next(e for e in emails if e["primary"])

        return primary["email"]