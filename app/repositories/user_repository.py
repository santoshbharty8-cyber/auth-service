import uuid
from sqlalchemy.orm import Session
from app.models.user import User

class UserRepository:

    def __init__(self, db: Session):
        self.db = db

    def find_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()
    
    def find_by_id(self, user_id):
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        return self.db.query(User).filter(User.id == user_id).first()
    
    def exists_by_email(self, email: str) -> bool:
        return self.db.query(User).filter(User.email == email).first() is not None

    def create(self, user: User):
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def save(self, user):
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def find_by_phone(self, phone: str):

        return (
            self.db.query(User)
            .filter(User.phone_number == phone)
            .first()
        )


    def create_phone_user(self, phone: str):

        user = User(
            phone_number=phone,
            phone_verified=True
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user