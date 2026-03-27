import uuid


# =========================================================
# ✅ ADMIN ROUTE
# =========================================================

def test_admin_route(client, create_admin_user):

    admin = create_admin_user()

    response = client.get(
        "/admin/",
        headers=admin["headers"]
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Welcome Admin"


# =========================================================
# ROLE TESTS
# =========================================================

def test_create_role_success(client, create_admin_user):

    admin = create_admin_user()

    response = client.post(
        "/admin/roles",
        json={"name": "manager"},
        headers=admin["headers"]
    )

    assert response.status_code == 200
    assert response.json()["name"] == "manager"


def test_create_role_already_exists(client, create_admin_user):

    admin = create_admin_user()

    # First create
    client.post(
        "/admin/roles",
        json={"name": "manager"},
        headers=admin["headers"]
    )

    # Duplicate
    response = client.post(
        "/admin/roles",
        json={"name": "manager"},
        headers=admin["headers"]
    )

    assert response.status_code == 400


def test_list_roles_success(client, create_admin_user):

    admin = create_admin_user()

    response = client.get(
        "/admin/roles",
        headers=admin["headers"]
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert any(role.get("name") == "admin" for role in response.json())


def test_list_permissions_success(client, create_admin_user):

    admin = create_admin_user()

    response = client.get(
        "/admin/permissions",
        headers=admin["headers"]
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert any(perm.get("name") == "admin:access" for perm in response.json())


# =========================================================
# PERMISSION TESTS
# =========================================================

def test_create_permission_success(client, create_admin_user):

    admin = create_admin_user()

    response = client.post(
        "/admin/permissions",
        json={"name": "reports:view"},
        headers=admin["headers"]
    )

    assert response.status_code == 200
    assert response.json()["name"] == "reports:view"


def test_create_permission_exists(client, create_admin_user):

    admin = create_admin_user()

    client.post(
        "/admin/permissions",
        json={"name": "reports:view"},
        headers=admin["headers"]
    )

    response = client.post(
        "/admin/permissions",
        json={"name": "reports:view"},
        headers=admin["headers"]
    )

    assert response.status_code == 400


# =========================================================
# ATTACH PERMISSION TO ROLE
# =========================================================

def test_attach_permission_success(client, db, create_admin_user):

    admin = create_admin_user()
    print(f"admin: {admin}")

    from app.models.role import Role
    role = db.query(Role).filter_by(name="admin").first()
    print(f"Role: {role.id} - {role.name}")

    response = client.post(
        f"/admin/roles/{str(role.id)}/permissions",
        json={"permission_name": "admin:manage"},
        headers=admin["headers"]
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Permission attached"


def test_attach_permission_not_found(client, create_admin_user):

    admin = create_admin_user()

    fake_id = uuid.uuid4()

    response = client.post(
        f"/admin/roles/{fake_id}/permissions",
        json={"permission_name": "invalid"},
        headers=admin["headers"]
    )

    assert response.status_code == 404


# =========================================================
# ASSIGN ROLE TO USER
# =========================================================

def test_assign_role_success(client, db,  create_admin_user):

    admin = create_admin_user()

    # get real user
    from app.models.user import User
    user = db.query(User).filter_by(email=admin["email"]).first()

    response = client.post(
        f"/admin/users/{user.id}/roles",
        json={"role_name": "admin"},
        headers=admin["headers"]
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Role assigned"


def test_assign_role_not_found(client, create_admin_user):

    admin = create_admin_user()

    fake_id = uuid.uuid4()

    response = client.post(
        f"/admin/users/{fake_id}/roles",
        json={"role_name": "invalid"},
        headers=admin["headers"]
    )

    assert response.status_code == 404