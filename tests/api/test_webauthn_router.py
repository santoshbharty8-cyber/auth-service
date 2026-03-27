import pytest
from unittest.mock import Mock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


from app.api import webauthn_router


def setup_wa_dependencies(mock_service):
    app.dependency_overrides.clear()
    app.dependency_overrides[webauthn_router.get_webauthn_service] = lambda: mock_service
    app.dependency_overrides[webauthn_router.get_current_user] = lambda: Mock()


def teardown_wa_dependencies():
    app.dependency_overrides.clear()


def test_start_registration_httpexception_passed_through(client):
    mock_service = Mock()
    mock_service.start_registration.side_effect = HTTPException(status_code=400, detail="Test error")
    setup_wa_dependencies(mock_service)

    response = client.get("/webauthn/register/start")

    teardown_wa_dependencies()
    assert response.status_code == 400


def test_start_registration_generic_exception_handled(client):
    mock_service = Mock()
    mock_service.start_registration.side_effect = ValueError("Test error")
    setup_wa_dependencies(mock_service)

    response = client.get("/webauthn/register/start")

    teardown_wa_dependencies()
    assert response.status_code == 500


def test_finish_registration_httpexception_passed_through(client):
    mock_service = Mock()
    mock_service.finish_registration.side_effect = HTTPException(status_code=400, detail="Test error")
    setup_wa_dependencies(mock_service)

    response = client.post("/webauthn/register/finish", json={})

    teardown_wa_dependencies()
    assert response.status_code == 400


def test_finish_registration_generic_exception_handled(client):
    mock_service = Mock()
    mock_service.finish_registration.side_effect = ValueError("Test error")
    setup_wa_dependencies(mock_service)

    response = client.post("/webauthn/register/finish", json={})

    teardown_wa_dependencies()
    assert response.status_code == 500


def test_finish_login_generic_exception_handled(client, monkeypatch):
    mock_webauthn_service = Mock()
    mock_webauthn_service.finish_login.side_effect = ValueError("Test error")
    monkeypatch.setattr("app.api.webauthn_router.get_webauthn_service", lambda: mock_webauthn_service)
    monkeypatch.setattr("app.api.webauthn_router.get_auth_service", lambda: Mock())

    response = client.post("/webauthn/login/finish", json={})
    assert response.status_code == 500