from app.models.audit_log import AuditLog


class AuditRepository:

    def __init__(self, db):
        self.db = db

    def create(self, log: AuditLog):
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log