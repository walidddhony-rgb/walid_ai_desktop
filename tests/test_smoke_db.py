"""Smoke test: database initializes and basic CRUD works."""
from db.database import Database


def test_database_initializes(tmp_path):
    db = Database(tmp_path / "test.db")
    assert db is not None
    rows = db.convs()
    assert isinstance(rows, list)
    db.close()


def test_database_add_conv(tmp_path):
    db = Database(tmp_path / "test.db")
    cid = db.add_conv("test conversation")
    assert cid is not None
    convs = db.convs()
    assert len(convs) == 1
    assert convs[0]["title"] == "test conversation"
    db.close()


def test_database_add_msg(tmp_path):
    db = Database(tmp_path / "test.db")
    cid = db.add_conv("test")
    mid = db.add_msg(cid, "user", "hello")
    assert mid is not None
    msgs = db.conv(cid)
    assert len(msgs) == 1
    assert msgs[0]["content"] == "hello"
    db.close()


def test_database_memory(tmp_path):
    db = Database(tmp_path / "test.db")
    db.add_memory("key1", "value1")
    mem = db.get_all_memory()
    assert "key1" in mem
    assert mem["key1"] == "value1"
    db.close()
