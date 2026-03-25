def test_register_success(client):

    response = client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "password": "StrongPass123"
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["email"] == "user@example.com"
    assert data["status"] == "PENDING"

def test_register_duplicate_email(client):

    client.post(
        "/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "StrongPass123"
        }
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "StrongPass123"
        }
    )

    assert response.status_code == 400