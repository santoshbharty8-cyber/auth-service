import uuid
from unittest.mock import Mock

from app.repositories.recovery_code_repository import RecoveryCodeRepository
from app.models.recovery_code import RecoveryCode


class MockDB:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []
        self.query_cls = None
        self._first_return = None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)

    def query(self, cls):
        self.query_cls = cls
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_return

    def set_first(self, value):
        self._first_return = value

    def delete(self):
        return 1


def test_create_calls_db_operations():
    db = MockDB()
    repo = RecoveryCodeRepository(db)

    rc = RecoveryCode(
        user_id=uuid.uuid4(),
        code_hash='ch',
        used=False
    )

    result = repo.create(rc)

    assert result is rc
    assert db.added == [rc]
    assert db.committed is True
    assert db.refreshed == [rc]


def test_find_valid_code_returns_record_or_none():
    db = MockDB()
    repo = RecoveryCodeRepository(db)

    expected = RecoveryCode(
        user_id=uuid.uuid4(),
        code_hash='hash1',
        used=False
    )
    db.set_first(expected)

    item = repo.find_valid_code(expected.user_id, 'hash1')
    assert item is expected
    assert db.query_cls is RecoveryCode

    db.set_first(None)
    item = repo.find_valid_code(expected.user_id, 'missing')
    assert item is None


def test_mark_used_sets_flag_and_commits():
    db = MockDB()
    repo = RecoveryCodeRepository(db)
    rc = RecoveryCode(user_id=uuid.uuid4(), code_hash='hash', used=False)

    repo.mark_used(rc)

    assert rc.used is True
    assert db.committed is True


def test_delete_by_user_queries_and_commits():
    db = MockDB()
    repo = RecoveryCodeRepository(db)

    repo.delete_by_user(uuid.uuid4())

    assert db.committed is True
