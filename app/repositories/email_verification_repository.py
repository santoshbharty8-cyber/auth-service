from sqlalchemy.orm import Session

from app.models.email_verification_token import EmailVerificationToken


class EmailVerificationRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, token: EmailVerificationToken):

        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)

        return token

    def find_by_hash(self, token_hash: str):

        return (
            self.db.query(EmailVerificationToken)
            .filter(EmailVerificationToken.token_hash == token_hash)
            .first()
        )

    def delete(self, token: EmailVerificationToken):

        self.db.delete(token)
        self.db.commit()

    def delete_by_user_id(self, user_id):

        (
            self.db.query(EmailVerificationToken)
            .filter(EmailVerificationToken.user_id == user_id)
            .delete()
        )

        self.db.commit()