import uuid
from types import SimpleNamespace
import pytest
from app.repositories.audit_repository import AuditRepository
from app.models.audit_log import AuditLog


class MockDB:
    """Mock database session for testing"""
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []
    
    def add(self, obj):
        self.added.append(obj)
    
    def commit(self):
        self.committed = True
    
    def refresh(self, obj):
        self.refreshed.append(obj)


def test_audit_repository_init():
    """Line 7: Test __init__ assigns db parameter"""
    mock_db = MockDB()
    repo = AuditRepository(mock_db)
    assert repo.db is mock_db


def test_audit_repository_create_adds_log():
    """Line 10: Test create() calls db.add()"""
    mock_db = MockDB()
    repo = AuditRepository(mock_db)
    
    log = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        event_type="LOGIN",
        event_status="SUCCESS",
        ip_address="127.0.0.1",
        user_agent="Mozilla/5.0",
        meta_info=None,
        created_at=None
    )
    
    result = repo.create(log)
    
    assert len(mock_db.added) == 1
    assert mock_db.added[0] is log


def test_audit_repository_create_commits_transaction():
    """Line 11: Test create() calls db.commit()"""
    mock_db = MockDB()
    repo = AuditRepository(mock_db)
    
    log = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        event_type="REGISTER",
        event_status="SUCCESS",
        ip_address="192.168.1.1",
        user_agent="Chrome",
        meta_info={"email": "test@example.com"},
        created_at=None
    )
    
    repo.create(log)
    
    assert mock_db.committed is True


def test_audit_repository_create_refreshes_log():
    """Line 12: Test create() calls db.refresh()"""
    mock_db = MockDB()
    repo = AuditRepository(mock_db)
    
    log = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=None,
        event_type="LOGOUT",
        event_status="SUCCESS",
        ip_address="10.0.0.1",
        user_agent="Safari",
        meta_info=None,
        created_at=None
    )
    
    repo.create(log)
    
    assert len(mock_db.refreshed) == 1
    assert mock_db.refreshed[0] is log


def test_audit_repository_create_returns_log():
    """Line 13: Test create() returns the log object"""
    mock_db = MockDB()
    repo = AuditRepository(mock_db)
    
    log = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        event_type="PASSWORD_RESET",
        event_status="SUCCESS",
        ip_address="172.16.0.1",
        user_agent="Firefox",
        meta_info={"action": "reset"},
        created_at=None
    )
    
    result = repo.create(log)
    
    assert result is log
    assert result.event_type == "PASSWORD_RESET"


def test_audit_repository_create_full_workflow():
    """Full integration test: create with all operations"""
    mock_db = MockDB()
    repo = AuditRepository(mock_db)
    
    log_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    log = SimpleNamespace(
        id=log_id,
        user_id=user_id,
        event_type="API_ACCESS",
        event_status="SUCCESS",
        ip_address="203.0.113.5",
        user_agent="Python-Client/1.0",
        meta_info={"endpoint": "/auth/login", "method": "POST"},
        created_at=None
    )
    
    result = repo.create(log)
    
    # Verify all operations were called in order
    assert result is log
    assert mock_db.committed
    assert log in mock_db.added
    assert log in mock_db.refreshed
    assert result.id == log_id
    assert result.user_id == user_id
