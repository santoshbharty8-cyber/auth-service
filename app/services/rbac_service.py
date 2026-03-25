class RBACService:

    def __init__(self, db):
        self.db = db

    def user_has_permission(self, user, permission_name: str):

        for role in user.roles:
            for perm in role.permissions:
                if perm.name == permission_name:
                    return True

        return False