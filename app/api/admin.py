import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.role import Role
from app.models.permission import Permission
from app.repositories.role_repository import RoleRepository
from app.repositories.permission_repository import PermissionRepository
from app.repositories.user_repository import UserRepository
from app.rbac.dependencies import require_permission
from app.schemas.rbac_schema import (
    RoleCreate,
    PermissionCreate,
    AssignPermissionToRole,
    AssignRoleToUser,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/")
def admin_route(
    current_user = Depends(require_permission("admin:access"))
):
    """
    Admin health check endpoint.

    Requires `admin:access` permission.

    Returns a simple confirmation message.
    """
    return {"message": "Welcome Admin"}

@router.post("/roles")
def create_role(
    request: RoleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("admin:manage")),
    
):
    """
    Create a new role.

    Requires `admin:manage` permission.

    Errors:
    - 400 if role already exists
    """

    role_repo = RoleRepository(db)

    if role_repo.find_by_name(request.name):
        raise HTTPException(status_code=400, detail="Role already exists")

    role = Role(name=request.name)

    return role_repo.create(role)

@router.post("/permissions")
def create_permission(
    request: PermissionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("admin:manage"))
):
    """
    Create a new permission.

    Requires `admin:manage` permission.

    Errors:
    - 400 if permission already exists
    """

    perm_repo = PermissionRepository(db)

    if perm_repo.find_by_name(request.name):
        raise HTTPException(status_code=400, detail="Permission exists")

    permission = Permission(name=request.name)

    return perm_repo.create(permission)

@router.post("/roles/{role_id}/permissions")
def attach_permission(
    role_id: uuid.UUID,
    request: AssignPermissionToRole,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("admin:manage"))
):
    """
    Attach a permission to a role.

    Requires `admin:manage` permission.

    Notes:
    - Adds permission to role
    - No-op if already assigned (depends on DB constraints)

    Errors:
    - 404 if role or permission not found
    """

    role_repo = RoleRepository(db)
    perm_repo = PermissionRepository(db)

    role = role_repo.find_by_id(role_id)
    permission = perm_repo.find_by_name(request.permission_name)

    if not role or not permission:
        raise HTTPException(status_code=404, detail="Not found")

    role.permissions.append(permission)
    db.commit()

    return {"message": "Permission attached"}

@router.post("/users/{user_id}/roles")
def assign_role_to_user(
    user_id: uuid.UUID,
    request: AssignRoleToUser,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("admin:manage"))
):
    """
    Assign a role to a user.

    Requires `admin:manage` permission.

    Notes:
    - User can have multiple roles

    Errors:
    - 404 if user or role not found
    """

    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)

    user = user_repo.find_by_id(user_id)
    role = role_repo.find_by_name(request.role_name)

    if not user or not role:
        raise HTTPException(status_code=404, detail="Not found")

    user.roles.append(role)
    db.commit()

    return {"message": "Role assigned"}

@router.get("/roles")
def list_roles(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("admin:manage"))
):
    """
    List all roles.

    Requires `admin:manage` permission.
    """
    role_repo = RoleRepository(db)
    return role_repo.list()

@router.get("/permissions")
def list_permissions(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("admin:manage"))
):
    """
    List all permissions.

    Requires `admin:manage` permission.
    """
    perm_repo = PermissionRepository(db)
    return perm_repo.list()