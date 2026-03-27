import uuid
from unittest.mock import Mock

from app.repositories.oauth_repository import OAuthRepository
from app.models.oauth_account import OAuthAccount


class MockDB:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []
        self.query_cls = None

    def query(self, cls):
        self.query_cls = cls
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return getattr(self, '_first_return', None)

    def set_first(self, value):
        self._first_return = value

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)


def test_find_by_provider_user_id_found():
    db = MockDB()
    repo = OAuthRepository(db)

    expected = OAuthAccount(
        user_id=uuid.uuid4(),
        provider='google',
        provider_user_id='abc',
        email='user@example.com',
        email_verified=True,
    )

    db.set_first(expected)

    result = repo.find_by_provider_user_id('google', 'abc')

    assert result is expected
    assert db.query_cls is OAuthAccount


def test_find_by_provider_user_id_not_found():
    db = MockDB()
    repo = OAuthRepository(db)

    db.set_first(None)

    result = repo.find_by_provider_user_id('github', 'does-not-exist')

    assert result is None
    assert db.query_cls is OAuthAccount


def test_create_account_calls_db_operations():
    db = MockDB()
    repo = OAuthRepository(db)

    account = OAuthAccount(
        user_id=uuid.uuid4(),
        provider='microsoft',
        provider_user_id='1234',
        email='test@microsoft.com',
        email_verified=False,
    )

    saved = repo.create(account)

    assert saved is account
    assert account in db.added
    assert db.committed is True
    assert account in db.refreshed
