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


def test_activate_user(client, auth):
    auth.login(username="admin", password="test")
    response = client.post("/admin/users/2/activate")
    assert response.status_code == 200
    assert response.json == {
        "activated": True,
    }

    with app.app_context():
        assert (
            get_db()
            .execute(
                "SELECT * FROM user WHERE username = 'other'",
            )
            .fetchone()["activated"] == 1
        )


@pytest.mark.parametrize("path", ("/admin/users",))
def test_login_required_get(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.json == {"message": "Not logged in"}


@pytest.mark.parametrize("path", ("/admin/users/1/activate",))
def test_login_required_post(client, path):
    response = client.post(path)
    assert response.status_code == 401
    assert response.json == {"message": "Not logged in"}


@pytest.mark.parametrize("path", ("/admin/users",))
def test_admin_required_get(client, auth, path):
    auth.login(username="test", password="test")
    response = client.get(path)
    assert response.status_code == 403
    assert response.json == {"message": "Not authorized"}


@pytest.mark.parametrize("path", ("/admin/users/1/activate",))
def test_admin_required_post(client, auth, path):
    auth.login(username="test", password="test")
    response = client.post(path)
    assert response.status_code == 403
    assert response.json == {"message": "Not authorized"}
