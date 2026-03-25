import pytest
import uuid
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from unittest.mock import Mock
from app.security.dependencies import get_current_user
from app.main import app


@pytest.fixture
def create_user(client):

    def _create_user(email=None, password="StrongPass123"):

        if email is None:
            email = f"user-{uuid.uuid4()}@test.com"

        response = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password
            }
        )

        data = response.json()

        return {
            "email": email,
            "password": password,
            "verification_token": data["verification_token"]
        }

    return _create_user



@pytest.fixture
def create_user_and_login(client):

    def _create_user(email=None, password="StrongPass123"):

        if email is None:
            email = f"user-{uuid.uuid4()}@test.com"

        # Register
        register = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password
            }
        )

        verification_token = register.json()["verification_token"]

        # Verify email
        client.post(
            "/auth/verify-email",
            json={"token": verification_token}
        )

        # Login
        login = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password
            }
        )

        tokens = login.json()

        return {
            "email": email,
            "password": password,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "headers": {
                "Authorization": f"Bearer {tokens['access_token']}"
            }
        }

    return _create_user

@pytest.fixture
def create_verified_user(client):

    def _create_user(email=None, password="StrongPass123"):

        if email is None:
            email = f"user-{uuid.uuid4()}@test.com"

        register = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password
            }
        )
        print("register json- ", register.json())
        verification_token = register.json()["verification_token"]

        client.post(
            "/auth/verify-email",
            json={"token": verification_token}
        )

        return {
            "email": email,
            "password": password
        }

    return _create_user

@pytest.fixture
def create_admin_user(client, db, create_verified_user):

    def _create_admin_user(email=None, password="StrongPass123"):

        if email is None:
            email = f"admin-{uuid.uuid4()}@test.com"

        # Create verified user
        user_data = create_verified_user(email=email, password=password)

        user = db.query(User).filter_by(email=user_data["email"]).first()
        assert user is not None

        # ---------------------------------
        # Ensure permissions exist
        # ---------------------------------
        access_perm = db.query(Permission).filter_by(name="admin:access").first()
        manage_perm = db.query(Permission).filter_by(name="admin:manage").first()

        if access_perm is None:
            access_perm = Permission(name="admin:access")
            db.add(access_perm)

        if manage_perm is None:
            manage_perm = Permission(name="admin:manage")
            db.add(manage_perm)

        db.commit()

        # ---------------------------------
        # Ensure admin role exists
        # ---------------------------------
        role = db.query(Role).filter_by(name="admin").first()

        if role is None:
            role = Role(name="admin")
            db.add(role)
            db.commit()
            db.refresh(role)

        # ---------------------------------
        # Attach permissions to role
        # ---------------------------------
        if access_perm not in role.permissions:
            role.permissions.append(access_perm)

        if manage_perm not in role.permissions:
            role.permissions.append(manage_perm)

        db.commit()

        # ---------------------------------
        # Attach role to user
        # ---------------------------------
        if role not in user.roles:
            user.roles.append(role)

        db.commit()
        db.refresh(user)

        # ---------------------------------
        # Login user
        # ---------------------------------
        login = client.post(
            "/auth/login",
            json={
                "email": user_data["email"],
                "password": password
            }
        )

        assert login.status_code == 200

        tokens = login.json()

        return {
            "email": user_data["email"],
            "password": password,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "headers": {
                "Authorization": f"Bearer {tokens['access_token']}"
            }
        }

    return _create_admin_user

@pytest.fixture
def google_payload():

    return {
        "sub": "google123",
        "email": "user@test.com",
        "email_verified": True,
        "name": "Test User",
        "picture": "avatar.png"
    }


@pytest.fixture
def auth_headers():

    user = Mock()
    user.id = uuid.uuid4()   # ✅ IMPORTANT
    user.email = "test@test.com"

    app.dependency_overrides[get_current_user] = lambda: user

    yield {
        "Authorization": "Bearer test-token"
    }

    app.dependency_overrides.clear()