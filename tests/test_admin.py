import pytest

from mmt_backend.db import get_db, User
from mmt_backend.mail import mail


def test_user_index(client, auth):
    auth.login(username="admin", password="test")
    response = client.get("/api/admin/users")
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
        response = client.post("/api/admin/users/2/activate")

        assert len(outbox) == 1
        assert outbox[0].recipients == ["other@example.com"]
        assert outbox[0].subject == "[mmt-py] Your account has been activated."

    assert response.status_code == 200
    assert response.json == {
        "message": "success",
    }

    with app.app_context():
        db = get_db()
        stmt = db.select(User).where(User.username == "other")
        user = db.session.execute(stmt).scalar()
        assert user.is_active


@pytest.mark.parametrize(
    ["path", "status_code", "message"],
    [
        ("/api/admin/users/10/activate", 404, "404 Not Found: User not found"),
        ("/api/admin/users/1/activate", 400, "400 Bad Request: User already activated"),
    ],
)
def test_activate_user_validation(client, auth, path, status_code, message):
    auth.login(username="admin", password="test")
    response = client.post(path)
    assert response.status_code == status_code
    assert response.json == {
        "error": message,
    }


@pytest.mark.parametrize("path", ("/api/admin/users",))
def test_login_required_get(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.json == {"message": "Not logged in"}


@pytest.mark.parametrize("path", ("/api/admin/users/1/activate",))
def test_login_required_post(client, path):
    response = client.post(path)
    assert response.status_code == 401
    assert response.json == {"message": "Not logged in"}


@pytest.mark.parametrize("path", ("/api/admin/users",))
def test_admin_required_get(client, auth, path):
    auth.login(username="test", password="test")
    response = client.get(path)
    assert response.status_code == 403
    assert response.json == {"message": "Not authorized"}


@pytest.mark.parametrize("path", ("/api/admin/users/1/activate",))
def test_admin_required_post(client, auth, path):
    auth.login(username="test", password="test")
    response = client.post(path)
    assert response.status_code == 403
    assert response.json == {"message": "Not authorized"}
