import pytest
from mmt_backend.db import get_db


def test_user_index(client, auth):
    auth.login(username="admin", password="test")
    response = client.get("/admin/users")
    assert response.status_code == 200
    assert len(response.json) == 3
    assert response.json[0] == (
        {
            "id": 3,
            "username": "admin",
            "email": "admin@example.com",
            "locale": "en",
            "activated": True,
            "admin": True,
            "can_upload": True,
        }
    )


@pytest.mark.parametrize("path", ("/admin/users",))
def test_login_required_get(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.json == {"message": "Not logged in"}


def test_admin_required(client, auth):
    auth.login(username="test", password="test")
    response = client.get("/admin/users")
    assert response.status_code == 403
    assert response.json == {"message": "Not authorized"}
