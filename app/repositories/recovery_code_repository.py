from sqlalchemy.orm import Session
from app.models.recovery_code import RecoveryCode


class RecoveryCodeRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, code: RecoveryCode):

        self.db.add(code)
        self.db.commit()
        self.db.refresh(code)

        return code

    def find_valid_code(self, user_id, code_hash):

        return (
            self.db.query(RecoveryCode)
            .filter(
                RecoveryCode.user_id == user_id,
                RecoveryCode.code_hash == code_hash,
                RecoveryCode.used == False
            )
            .first()
        )

    def mark_used(self, code: RecoveryCode):

        code.used = True
        self.db.commit()

    def delete_by_user(self, user_id):

        (
            self.db.query(RecoveryCode)
            .filter(RecoveryCode.user_id == user_id)
            .delete()
        )

        self.db.commit()