from app.models.refresh_token import RefreshToken

class TokenRepository:

    def __init__(self, db):
        self.db = db

    def create(self, token):
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def find_by_hash(self, token_hash):
        return self.db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False
        ).first()

    def revoke(self, token):
        token.revoked = True
        self.db.commit()

    def revoke_all_for_user(self, user_id):
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id
        ).update({"revoked": True})
        self.db.commit()