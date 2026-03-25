from sqlalchemy.orm import Session
from app.models.webauthn_credential import WebAuthnCredential

class WebAuthnRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, credential):
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        return credential

    def update(self, credential):
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        return credential

    def find_by_user(self, user_id):
        return self.db.query(WebAuthnCredential).filter(
            WebAuthnCredential.user_id == user_id
        ).all()

    def find_by_credential_id(self, credential_id):
        return self.db.query(WebAuthnCredential).filter(
            WebAuthnCredential.credential_id == credential_id
        ).first()