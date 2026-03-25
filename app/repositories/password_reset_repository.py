from app.models.password_reset_token import PasswordResetToken

class PasswordResetRepository:

    def __init__(self, db):
        self.db = db

    def create(self, token):
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def find_by_hash(self, token_hash):
        return (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.token_hash == token_hash)
            .first()
        )

    def delete(self, token):
        self.db.delete(token)
        self.db.commit()