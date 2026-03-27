import uuid
from types import SimpleNamespace

from app.models.refresh_token import RefreshToken
from app.repositories.token_repository import TokenRepository


class MockDB:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []
        self.queries = []
        self.query_cls = None
        self._first_output = None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)

    def query(self, cls):
        self.query_cls = cls
        self.queries.append(('query', cls))
        return self

    def filter(self, *args, **kwargs):
        self.queries.append(('filter', args))
        return self

    def first(self):
        self.queries.append(('first', None))
        return self._first_output

    def update(self, values):
        self.queries.append(('update', values))
        return 1

    def set_first(self, value):
        self._first_output = value


def test_token_repository_init_and_create():
    db = MockDB()
    repo = TokenRepository(db)

    token = RefreshToken(user_id=uuid.uuid4(), token_hash='abc', revoked=False)

    ret = repo.create(token)

    assert repo.db is db
    assert db.added == [token]
    assert db.committed
    assert db.refreshed == [token]
    assert ret is token


def test_find_by_hash_queries_and_returns():
    db = MockDB()
    repo = TokenRepository(db)

    expected = RefreshToken(user_id=uuid.uuid4(), token_hash='xyz', revoked=False)
    db.set_first(expected)

    result = repo.find_by_hash('xyz')

    assert result is expected
    assert db.query_cls is RefreshToken

    # filter() should be called once and should include both conditions
    filter_calls = [c for c in db.queries if c[0] == 'filter']
    assert len(filter_calls) == 1
    exprs = filter_calls[0][1]
    assert len(exprs) == 2
    assert 'token_hash' in str(exprs[0])
    assert 'revoked' in str(exprs[1])


def test_revoke_sets_token_and_commits():
    db = MockDB()
    repo = TokenRepository(db)

    token = SimpleNamespace(revoked=False)

    repo.revoke(token)

    assert token.revoked is True
    assert db.committed is True


def test_revoke_all_for_user_updates_and_commits():
    db = MockDB()
    repo = TokenRepository(db)

    user_id = uuid.uuid4()
    repo.revoke_all_for_user(user_id)

    assert db.query_cls is RefreshToken
    assert any(item[0] == 'update' and item[1] == {'revoked': True} for item in db.queries)
    assert db.committed is True
