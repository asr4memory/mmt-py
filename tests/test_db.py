import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from mmt_backend.db import get_db


@pytest.mark.skip(reason="not sure if new db can be closed yet")
def test_get_close_db(app):
    with app.app_context():
        db = get_db()
        assert db is get_db()

        with pytest.raises(ProgrammingError) as e:
            db.session.execute(text("SELECT 1"))

        assert "closed" in str(e.value)


def test_init_db_command(runner, monkeypatch):
    class Recorder(object):
        called = False

    def fake_init_db():
        Recorder.called = True

    monkeypatch.setattr("mmt_backend.db.init_db", fake_init_db)
    result = runner.invoke(args=["init-db"])
    assert "Initialized" in result.output
    assert Recorder.called
