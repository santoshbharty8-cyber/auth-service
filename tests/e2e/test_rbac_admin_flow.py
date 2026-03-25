def test_admin_access_flow(client, create_admin_user):

    admin = create_admin_user()

    response = client.get(
        "/admin",
        headers=admin["headers"]
    )

    assert response.status_code == 200


def test_admin_forbidden_for_normal_user(client, create_user_and_login):

    user = create_user_and_login()

    response = client.get(
        "/admin",
        headers=user["headers"]
    )

    assert response.status_code == 403

def test_admin_create_role(client, create_admin_user):

    admin = create_admin_user()

    response = client.post(
        "/admin/roles",
        json={"name": "manager"},
        headers=admin["headers"]
    )

    assert response.status_code == 200

def test_admin_create_permission(client, create_admin_user):

    admin = create_admin_user()

    response = client.post(
        "/admin/permissions",
        json={"name": "reports:view"},
        headers=admin["headers"]
    )

    assert response.status_code == 200

