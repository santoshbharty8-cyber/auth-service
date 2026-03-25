def test_force_logout_all_devices_flow(client):

    register = client.post(
        "/auth/register",
        json={"email": "force_e2e@test.com", "password": "StrongPass123"}
    )

    token = register.json()["verification_token"]

    client.post("/auth/verify-email", json={"token": token})

    login = client.post(
        "/auth/login",
        json={"email": "force_e2e@test.com", "password": "StrongPass123"}
    )

    access_token = login.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    # Force logout all
    client.post("/auth/force-logout-all", headers=headers)

    # Token should be invalid
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401