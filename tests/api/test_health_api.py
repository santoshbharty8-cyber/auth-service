def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "healthy"
    assert body["service"] == "auth-system"
    assert "timestamp" in body


def test_liveness_endpoint(client):
    response = client.get("/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_starting(client, monkeypatch):
    import app.core.startup_state as startup_state

    monkeypatch.setattr(startup_state, "startup_complete", False)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "Service starting"


def test_readiness_dependency_not_ready(client, monkeypatch):
    import app.core.startup_state as startup_state
    import app.api.health

    monkeypatch.setattr(startup_state, "startup_complete", True)
    monkeypatch.setattr(app.api.health, "check_database", lambda: False)
    monkeypatch.setattr(app.api.health, "check_redis", lambda: True)

    response = client.get("/ready")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["status"] == "not_ready"
    assert detail["checks"]["database"] is False
    assert detail["checks"]["redis"] is True


def test_readiness_dependency_error(client, monkeypatch):
    import app.core.startup_state as startup_state
    import app.api.health

    monkeypatch.setattr(startup_state, "startup_complete", True)

    def _fail_check():
        raise RuntimeError("db unreachable")

    monkeypatch.setattr(app.api.health, "check_database", _fail_check)
    monkeypatch.setattr(app.api.health, "check_redis", lambda: True)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "Dependency check failed"


def test_readiness_all_ready(client, monkeypatch):
    import app.core.startup_state as startup_state
    import app.api.health

    monkeypatch.setattr(startup_state, "startup_complete", True)
    monkeypatch.setattr(app.api.health, "check_database", lambda: True)
    monkeypatch.setattr(app.api.health, "check_redis", lambda: True)

    response = client.get("/ready")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] is True
    assert body["checks"]["redis"] is True
