from datetime import datetime, timedelta, UTC
from sqlalchemy import text
from app.models.email_verification_token import EmailVerificationToken
from app.models.user import User


def test_login_blocked_if_email_not_verified(client, create_user):

    user = create_user(email="pending@test.com")

    response = client.post(
        "/auth/login",
        json={
            "email": user["email"],
            "password": user["password"]
        }
    )

    assert response.status_code == 403


def test_verification_token_created(client, db, create_user):

    create_user(email="verify@test.com")

    token = db.query(EmailVerificationToken).first()

    assert token is not None


def test_email_verification_success(client, create_user):

    user = create_user(email="activate@test.com")

    response = client.post(
        "/auth/verify-email",
        json={"token": user["verification_token"]}
    )

    assert response.status_code == 200


def test_login_after_email_verification(client, create_user):

    user = create_user(email="verified@test.com")

    client.post(
        "/auth/verify-email",
        json={"token": user["verification_token"]}
    )

    response = client.post(
        "/auth/login",
        json={
            "email": user["email"],
            "password": user["password"]
        }
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_invalid_verification_token(client):

    response = client.post(
        "/auth/verify-email",
        json={"token": "invalidtoken"}
    )

    assert response.status_code == 400


def test_expired_verification_token(client, db, create_user):

    user = create_user(email="expired@test.com")

    db.execute(
        text("UPDATE email_verification_tokens SET expires_at = :time"),
        {"time": datetime.now(UTC) - timedelta(hours=1)}
    )
    db.commit()

    response = client.post(
        "/auth/verify-email",
        json={"token": user["verification_token"]}
    )

    assert response.status_code == 400


def test_verification_activates_account(client, db, create_user):

    user = create_user(email="status@test.com")

    client.post(
        "/auth/verify-email",
        json={"token": user["verification_token"]}
    )

    user_db = db.query(User).filter_by(email=user["email"]).first()

    assert user_db.status == "ACTIVE"


def test_resend_verification_success(client, create_user):

    user = create_user(email="resend@test.com")

    response = client.post(
        "/auth/resend-verification",
        json={"email": user["email"]}
    )

    assert response.status_code == 200
    assert "verification_token" in response.json()


def test_resend_verification_for_verified_user(client, create_user):

    user = create_user(email="verified@test.com")

    client.post(
        "/auth/verify-email",
        json={"token": user["verification_token"]}
    )

    response = client.post(
        "/auth/resend-verification",
        json={"email": user["email"]}
    )

    assert response.status_code == 400


def test_resend_verification_user_not_found(client):

    response = client.post(
        "/auth/resend-verification",
        json={"email": "notfound@test.com"}
    )

    assert response.status_code == 404