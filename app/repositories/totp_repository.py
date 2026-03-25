from sqlalchemy.orm import Session
from app.models.totp_credential import TOTPCredential


class TOTPRepository:

    def __init__(self, db: Session):
        self.db = db

    def find_by_user(self, user_id):

        return (
            self.db.query(TOTPCredential)
            .filter(TOTPCredential.user_id == user_id)
            .first()
        )

    def create(self, credential):

        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)

        return credential

    def enable(self, credential):

        credential.is_enabled = True
        self.db.commit()