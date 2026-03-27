import uuid
from app.models.totp_credential import TOTPCredential
from app.repositories.totp_repository import TOTPRepository


class MockDB:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []
        self.query_cls = None
        self._first_output = None

    def query(self, cls):
        self.query_cls = cls
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_output

    def set_first(self, value):
        self._first_output = value

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)


def test_find_by_user_returns_record():
    db = MockDB()
    repo = TOTPRepository(db)

    expected = TOTPCredential(user_id=uuid.uuid4(), secret='abc', is_enabled=False)
    db.set_first(expected)

    result = repo.find_by_user(expected.user_id)
    assert result is expected
    assert db.query_cls is TOTPCredential


def test_create_records_db_operation():
    db = MockDB()
    repo = TOTPRepository(db)

    credential = TOTPCredential(user_id=uuid.uuid4(), secret='abc', is_enabled=False)
    result = repo.create(credential)

    assert result is credential
    assert db.added == [credential]
    assert db.committed
    assert db.refreshed == [credential]


def test_enable_sets_flag_and_commit():
    db = MockDB()
    repo = TOTPRepository(db)

    credential = TOTPCredential(user_id=uuid.uuid4(), secret='abc', is_enabled=False)
    repo.enable(credential)

    assert credential.is_enabled is True
    assert db.committed is True
