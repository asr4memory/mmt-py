import pytest

from mmt_backend.db import get_db
from mmt_backend.mail import mail


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
            "upload_count": 0,
        }
    )


def test_activate_user(client, auth, app):
    with mail.record_messages() as outbox:
        auth.login(username="admin", password="test")
        response = client.post("/admin/users/2/activate")

        assert len(outbox) == 1
        assert outbox[0].recipients == ["other@example.com"]
        assert outbox[0].subject == "[mmt-py] Your account has been activated."

    assert response.status_code == 200
    assert response.json == {
        "message": "success",
    }

    with app.app_context():
        assert (
            get_db()
            .execute("SELECT * FROM user WHERE username = 'other'")
            .fetchone()["activated"]
            == 1
        )


@pytest.mark.parametrize(["path", "status_code", "message"], [
    ("/admin/users/10/activate", 404, "User not found"),
    ("/admin/users/1/activate", 400, "User already activated")
])
def test_activate_user_validation(client, auth, path, status_code, message):
    auth.login(username="admin", password="test")
    response = client.post(path)
    assert response.status_code == status_code
    assert response.json == {
        "message": message,
    }


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
