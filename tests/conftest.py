import os
import sys
import pytest
from unittest.mock import Mock

# -----------------------------
# Setup project path + env
# -----------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["ENV"] = "testing"

# -----------------------------
# App imports
# -----------------------------
from app.main import app
from app.cache.redis_client import redis_client
from app.core.database import get_db
from app.dependencies.auth_dependencies import get_auth_service

from tests.fixtures.database import get_test_db
from tests.fixtures.client import get_test_client
from tests.factories.auth_service_factory import create_auth_service

# -----------------------------
# Disable rate limiting (global)
# -----------------------------
@pytest.fixture(autouse=True)
def disable_rate_limit():
    app.state.rate_limit_disabled = True
    yield
    app.state.rate_limit_disabled = False


# -----------------------------
# Clean Redis (rate limit + oauth)
# -----------------------------
@pytest.fixture(autouse=True)
def clear_redis():
    for key in redis_client.scan_iter("ratelimit:*"):
        redis_client.delete(key)

    for key in redis_client.scan_iter("oauth_state:*"):
        redis_client.delete(key)

    for key in redis_client.scan_iter("webauthn_*"):
        redis_client.delete(key)

    yield


# -----------------------------
# DB fixture
# -----------------------------
@pytest.fixture
def db():
    yield from get_test_db()


# -----------------------------
# Client fixture
# -----------------------------
@pytest.fixture
def client(db):

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    test_client = get_test_client()

    yield test_client

    app.dependency_overrides.pop(get_db, None)



# =========================================================
# 🔧 GENERIC DEPENDENCY OVERRIDE (BEST PRACTICE)
# =========================================================

@pytest.fixture
def override_dep():
    overrides = {}

    def _override(dep, impl):
        overrides[dep] = impl
        app.dependency_overrides[dep] = impl

    yield _override

    # cleanup only what we set
    for dep in overrides:
        app.dependency_overrides.pop(dep, None)

# -----------------------------
# Helper: mock AuthService
# -----------------------------
def create_mock_auth_service():
    service = Mock()

    # Default behaviors
    service.request_magic_link.return_value = {
        "message": "Magic login link sent"
    }

    service.login_with_magic_link.return_value = {
        "access_token": "token"
    }

    service.approve_login.return_value = {
        "access_token": "token"
    }

    return service


# -----------------------------
# Fixture: override AuthService
# -----------------------------
@pytest.fixture
def mock_auth_service():
    service = create_mock_auth_service()

    app.dependency_overrides[get_auth_service] = lambda: service

    yield service

    app.dependency_overrides.pop(get_auth_service, None)

@pytest.fixture
def real_auth_service():
    service = create_auth_service()

    app.dependency_overrides[get_auth_service] = lambda: service

    yield service

    app.dependency_overrides.pop(get_auth_service, None)
    
# -----------------------------
# Pytest plugins
# -----------------------------
pytest_plugins = [
    "tests.fixtures.oauth",
    "tests.fixtures.redis",
    "tests.fixtures.auth"
    
]