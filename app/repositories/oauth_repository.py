from sqlalchemy.orm import Session
from app.models.oauth_account import OAuthAccount


class OAuthRepository:

    def __init__(self, db: Session):
        self.db = db

    def find_by_provider_user_id(self, provider, provider_user_id):

        return (
            self.db.query(OAuthAccount)
            .filter(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
            .first()
        )

    def create(self, account: OAuthAccount):

        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)

        return account