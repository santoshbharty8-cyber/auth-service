from app.core.database import SessionLocal
from app.models.role import Role
from app.models.permission import Permission
from app.models.user import User


def seed():

    db = SessionLocal()

    # -------------------------
    # Create Permissions
    # -------------------------
    permissions = [
        "admin:access",
        "audit:view",
        "user:create",
        "user:delete",
        "session:view",
        "admin:manage",
    ]

    permission_objects = []

    for perm_name in permissions:
        perm = db.query(Permission).filter_by(name=perm_name).first()
        if not perm:
            perm = Permission(name=perm_name)
            db.add(perm)
            db.commit()
            db.refresh(perm)
        permission_objects.append(perm)

    # -------------------------
    # Create ADMIN Role
    # -------------------------
    admin_role = db.query(Role).filter_by(name="ADMIN").first()

    if not admin_role:
        admin_role = Role(name="ADMIN")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)

    # -------------------------
    # Attach Permissions to Role
    # -------------------------
    admin_role.permissions = permission_objects
    db.commit()

    # -------------------------
    # Assign ADMIN Role to User
    # -------------------------
    user_email = "santosh@example.com"

    user = db.query(User).filter_by(email=user_email).first()

    if user:
        user.roles.append(admin_role)
        db.commit()
        print("Admin role assigned to user.")
    else:
        print("User not found.")

    db.close()


if __name__ == "__main__":
    seed()