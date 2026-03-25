from app.models.permission import Permission

class PermissionRepository:

    def __init__(self, db):
        self.db = db

    def create(self, permission):
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def find_by_name(self, name):
        return self.db.query(Permission).filter(Permission.name == name).first()