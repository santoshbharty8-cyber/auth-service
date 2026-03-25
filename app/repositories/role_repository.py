from app.models.role import Role

class RoleRepository:

    def __init__(self, db):
        self.db = db

    def create(self, role):
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def find_by_id(self, role_id):
        return self.db.query(Role).filter(Role.id == role_id).first()

    def find_by_name(self, name):
        return self.db.query(Role).filter(Role.name == name).first()