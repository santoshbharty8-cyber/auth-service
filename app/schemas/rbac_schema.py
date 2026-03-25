from pydantic import BaseModel


class RoleCreate(BaseModel):
    name: str


class PermissionCreate(BaseModel):
    name: str


class AssignPermissionToRole(BaseModel):
    permission_name: str


class AssignRoleToUser(BaseModel):
    role_name: str