from uuid import UUID
from app.models.user_session import UserSession


class SessionRepository:

    def __init__(self, db):
        self.db = db

    def create(self, session: UserSession):
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def find_by_id(self, session_id):
        return self.db.query(UserSession).filter(
            UserSession.id == UUID(session_id)
        ).first()

    def find_by_hash(self, token_hash: str):
        return self.db.query(UserSession).filter(
            UserSession.refresh_token_hash == token_hash,
            UserSession.is_active == True
        ).first()

    def revoke(self, session: UserSession):

        self.db.query(UserSession).filter(
            UserSession.id == session.id
        ).update({"is_active": False})

        self.db.commit()

    def revoke_all_for_user(self, user_id):
        self.db.query(UserSession).filter(
            UserSession.user_id == user_id
        ).update({"is_active": False})
        self.db.commit()

    def find_active_by_user(self, user_id):
        return self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).all()
    
    def save(self, session):  # ✅ NEW
        self.db.commit()
        self.db.refresh(session)
        return session