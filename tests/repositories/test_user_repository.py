import uuid
from app.models.user import User
from app.repositories.user_repository import UserRepository


class MockDB:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []
        self.query_cls = None
        self._first_output = None
        self._all_output = []

    def query(self, cls):
        self.query_cls = cls
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_output

    def all(self):
        return self._all_output

    def set_first(self, value):
        self._first_output = value

    def set_all(self, value):
        self._all_output = value

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)


def test_find_by_email_and_exists_by_email():
    db = MockDB()
    repo = UserRepository(db)

    u = User(id=uuid.uuid4(), email='test@example.com')
    db.set_first(u)

    assert repo.find_by_email('test@example.com') is u
    assert repo.exists_by_email('test@example.com') is True


def test_find_by_id_with_string_and_uuid():
    db = MockDB()
    repo = UserRepository(db)

    u = User(id=uuid.uuid4(), email='id@example.com')
    db.set_first(u)

    res1 = repo.find_by_id(str(u.id))
    assert res1 is u
    res2 = repo.find_by_id(u.id)
    assert res2 is u


def test_create_save_and_find_by_phone():
    db = MockDB()
    repo = UserRepository(db)

    new_user = User(email='phone@example.com', phone_number='12345', phone_verified=False)
    out = repo.create(new_user)

    assert out is new_user
    assert db.added == [new_user]
    assert db.committed
    assert db.refreshed == [new_user]

    # save should commit and refresh again
    db.committed = False; db.refreshed = []
    out2 = repo.save(new_user)
    assert out2 is new_user
    assert db.committed
    assert db.refreshed == [new_user]

    # find_by_phone
    db.set_first(new_user)
    assert repo.find_by_phone('12345') is new_user


def test_create_phone_user_branch():
    db = MockDB()
    repo = UserRepository(db)

    result = repo.create_phone_user('555-0000')
    assert result.phone_number == '555-0000'
    assert result.phone_verified is True
    assert db.committed
    assert db.refreshed == [result]
