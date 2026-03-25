from fastapi import Depends, HTTPException
from app.security.dependencies import get_current_user
from app.services.rbac_service import RBACService
from app.core.database import get_db
from sqlalchemy.orm import Session


def require_permission(permission_name: str):

    def permission_checker(
        current_user = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):

        rbac_service = RBACService(db)

        if not rbac_service.user_has_permission(current_user, permission_name):
            raise HTTPException(
                status_code=403,
                detail="Permission denied"
            )

        return current_user

    return permission_checker