import json
import pytest
from types import SimpleNamespace

from app.workers import audit_worker

def test_save_to_db_success(monkeypatch):
    calls = []

    class DummySession:
        def add(self, obj):
            calls.append(("add", obj))

        def commit(self):
            calls.append(("commit",))

        def close(self):
            calls.append(("close",))

    monkeypatch.setattr(
        audit_worker,
        "SessionLocal",
        lambda: DummySession()
    )

    event = {
        "user_id": "u1",
        "event_type": "LOGIN",
        "event_status": "SUCCESS"
    }

    audit_worker.save_to_db(event)

    assert any(c[0] == "add" for c in calls)
    assert ("commit",) in calls
    assert ("close",) in calls

def test_start_worker_no_event(monkeypatch):

    call_count = {"n": 0}

    def fake_brpoplpush(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None  # triggers continue
        raise SystemExit  # ✅ NOT caught → exits loop

    monkeypatch.setattr(
        "app.workers.audit_worker.redis_client.brpoplpush",
        fake_brpoplpush
    )

    with pytest.raises(SystemExit):
        from app.workers.audit_worker import start_worker
        start_worker()

def test_start_worker_success(monkeypatch):

    import json

    event = {"event_type": "LOGIN", "event_status": "SUCCESS"}

    call_count = {"n": 0}

    def fake_brpoplpush(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return json.dumps(event)
        raise SystemExit  # ✅ exit cleanly

    monkeypatch.setattr(
        "app.workers.audit_worker.redis_client.brpoplpush",
        fake_brpoplpush
    )

    monkeypatch.setattr(
        "app.workers.audit_worker.save_to_db",
        lambda e: None
    )

    monkeypatch.setattr(
        "app.workers.audit_worker.redis_client.lrem",
        lambda *a, **k: None
    )

    with pytest.raises(SystemExit):
        from app.workers.audit_worker import start_worker
        start_worker()

def test_start_worker_exception(monkeypatch):

    def fake_brpoplpush(*args, **kwargs):
        raise Exception("boom")

    monkeypatch.setattr(
        "app.workers.audit_worker.redis_client.brpoplpush",
        fake_brpoplpush
    )

    # break loop AFTER exception handling
    monkeypatch.setattr(
        "app.workers.audit_worker.time.sleep",
        lambda x: (_ for _ in ()).throw(SystemExit())
    )

    with pytest.raises(SystemExit):
        from app.workers.audit_worker import start_worker
        start_worker()