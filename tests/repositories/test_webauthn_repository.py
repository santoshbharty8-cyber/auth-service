import uuid
from app.repositories.webauthn_repository import WebAuthnRepository
from app.models.webauthn_credential import WebAuthnCredential


class MockDB:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []
        self.query_cls = None
        self._all_output = []
        self._first_output = None

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

    def all(self):
        return self._all_output

    def first(self):
        return self._first_output

    def set_all(self, value):
        self._all_output = value

    def set_first(self, value):
        self._first_output = value


def test_create_update_returns_credential_and_db_ops():
    db = MockDB()
    repo = WebAuthnRepository(db)

    credential = WebAuthnCredential(
        user_id=uuid.uuid4(),
        credential_id='cred-1',
        public_key='pubkey',
    )

    res1 = repo.create(credential)
    assert res1 is credential
    assert db.added == [credential]
    assert db.committed
    assert db.refreshed == [credential]

    # Reset db state and verify update uses same pattern
    db.added.clear(); db.committed = False; db.refreshed.clear()
    res2 = repo.update(credential)
    assert res2 is credential
    assert db.added == [credential]
    assert db.committed
    assert db.refreshed == [credential]


def test_find_by_user_returns_all_records():
    db = MockDB()
    repo = WebAuthnRepository(db)

    u = uuid.uuid4()
    expected = [WebAuthnCredential(user_id=u, credential_id='cred2', public_key='k')]
    db.set_all(expected)

    result = repo.find_by_user(u)
    assert result == expected
    assert db.query_cls is WebAuthnCredential


def test_find_by_credential_id_returns_one():
    db = MockDB()
    repo = WebAuthnRepository(db)

    expected = WebAuthnCredential(user_id=uuid.uuid4(), credential_id='cred3', public_key='k')
    db.set_first(expected)

    result = repo.find_by_credential_id('cred3')
    assert result is expected
    assert db.query_cls is WebAuthnCredential
