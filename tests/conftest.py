import os
import tempfile

import pytest

from mmt_backend import create_app
from mmt_backend.db import get_db, init_db
from add_data import add_data


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()

    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}"}
    )

    with app.app_context():
        init_db()
        add_data()

    yield app

    os.close(db_fd)
    os.unlink(db_path)


class AuthActions(object):
    def __init__(self, client):
        self._client = client

    def login(self, username="test", password="test"):
        return self._client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )

    def logout(self):
        return self._client.post("/api/auth/logout")


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def auth(client):
    return AuthActions(client)
