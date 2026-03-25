from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.webauthn_repository import WebAuthnRepository
from app.repositories.user_repository import UserRepository
from app.services.webauthn_service import WebAuthnService


def get_webauthn_service(
    db: Session = Depends(get_db)
):

    webauthn_repo = WebAuthnRepository(db)
    user_repo = UserRepository(db)

    return WebAuthnService(
        webauthn_repo=webauthn_repo,
        user_repo=user_repo
    )