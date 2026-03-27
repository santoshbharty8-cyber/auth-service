import uuid
from app.models.role import Role
from app.repositories.role_repository import RoleRepository


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


def test_create_and_find_by_id_kind():
    db = MockDB()
    repo = RoleRepository(db)

    r = Role(id=uuid.uuid4(), name='admin')
    out = repo.create(r)

    assert out is r
    assert db.committed
    assert db.refreshed == [r]

    db.set_first(r)
    assert repo.find_by_id(str(r.id)) is r
    assert repo.find_by_id(r.id) is r


def test_find_by_name_and_list():
    db = MockDB()
    repo = RoleRepository(db)

    r1 = Role(id=uuid.uuid4(), name='user')
    r2 = Role(id=uuid.uuid4(), name='admin')
    db.set_first(r1)
    db.set_all([r1, r2])

    assert repo.find_by_name('user') is r1
    assert repo.list() == [r1, r2]
