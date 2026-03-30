from app.core.config import settings

def get_oauth_redirect_uri(provider: str) -> str:
    return f"{settings.BASE_URL}/auth/oauth/{provider}/callback"