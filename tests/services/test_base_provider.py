import pytest
from app.auth_providers.base import BaseAuthProvider
from app.models import User


class DummyProvider(BaseAuthProvider):
    def authenticate(self, data):
        if data.get("email") == "ok@example.com":
            return User(email="ok@example.com")
        return None


def test_base_auth_provider_is_abstract():
    with pytest.raises(TypeError, match="abstract"):
        # pylint: disable=abstract-class-instantiated
        BaseAuthProvider()  # cannot instantiate abstract base class


def test_dummy_provider_authenticate_success():
    provider = DummyProvider()
    user = provider.authenticate({"email": "ok@example.com"})
    assert isinstance(user, User)
    assert user.email == "ok@example.com"


def test_dummy_provider_authenticate_failure():
    provider = DummyProvider()
    assert provider.authenticate({"email": "bad@example.com"}) is None

def test_child_without_implementation_fails():
    class BadProvider(BaseAuthProvider):
        pass

    with pytest.raises(TypeError):
        BadProvider()