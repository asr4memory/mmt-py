import pytest
from flask import g, session
from mmt_backend.db import get_db
from mmt_backend.mail import mail


def test_register(client, app):
    with mail.record_messages() as outbox:
        response = client.post(
            "/auth/register",
            json={"username": "a", "email": "a@a.com", "password": "a"},
        )
        assert len(outbox) == 1
        assert outbox[0].subject == "[mmt-py] A new user has registered."

    assert response.status_code == 201
    assert response.json["username"] == "a"
    assert response.json["email"] == "a@a.com"

    with app.app_context():
        assert (
            get_db()
            .execute(
                "SELECT * FROM user WHERE username = 'a'",
            )
            .fetchone()
            is not None
        )


@pytest.mark.parametrize(
    ("username", "email", "password", "message"),
    (
        ("", "", "", "Username is required."),
        ("a", "", "", "Email is required."),
        ("a", "a@a.com", "", "Password is required."),
        ("test", "test@example.com", "test", "User is already registered."),
    ),
)
def test_register_validate_input(client, username, email, password, message):
    response = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert response.status_code == 403
    assert response.json["message"] == message


def test_login(client, auth):
    response = client.post("/auth/login", json={"username": "test", "password": "test"})
    assert response.status_code == 200
    assert response.json["username"] == "test"
    assert response.json["email"] == "test@example.com"
    assert response.json["locale"] == "en"

    with client:
        client.get("/")
        assert session["user_id"] == 1
        assert g.user["username"] == "test"


def test_login_check_activated(app, client, auth):
    # change the user to not activated
    with app.app_context():
        db = get_db()
        db.execute("UPDATE user SET activated = false WHERE id = 1")
        db.commit()

    response = client.post("/auth/login", json={"username": "test", "password": "test"})
    assert response.status_code == 403
    assert response.json["code"] == "user_not_activated"
    assert response.json["message"] == "User has not been activated yet."


@pytest.mark.parametrize(
    ("username", "password", "code", "message"),
    (
        (
            "a",
            "test",
            "username_password_mismatch",
            "Username and password do not match.",
        ),
        (
            "test",
            "a",
            "username_password_mismatch",
            "Username and password do not match.",
        ),
    ),
)
def test_login_validate_input(client, auth, username, password, code, message):
    response = client.post(
        "/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 403
    assert response.json["code"] == code
    assert response.json["message"] == message


def test_logout(client, auth):
    auth.login()

    with client:
        response = client.post("/auth/logout")
        assert response.status_code == 200
        assert "user_id" not in session


def test_user(client, auth):
    auth.login()

    with client:
        response = client.get("/auth/user")
        assert response.status_code == 200
        assert response.json["username"] == "test"
        assert response.json["email"] == "test@example.com"
        assert response.json["locale"] == "en"


def test_user_update(client, auth):
    auth.login()

    with client:
        response = client.post("/auth/user", json={"locale": "de"})
        assert response.status_code == 200
        assert response.json["username"] == "test"
        assert response.json["email"] == "test@example.com"
        assert response.json["locale"] == "de"


@pytest.mark.parametrize(
    ("locale", "message"),
    (
        (
            None,
            "Locale is required.",
        ),
        (
            "fr",
            "Locale is not supported.",
        ),
    ),
)
def test_user_update_validate_input(client, auth, locale, message):
    auth.login()
    response = client.post(
        "/auth/user", json={"locale": locale}
    )
    assert response.status_code == 400
    assert response.json["message"] == message


@pytest.mark.parametrize('path', ["/auth/user"])
def test_login_required_get(client, path):
    with client:
        response = client.get(path)
        assert response.status_code == 401


@pytest.mark.parametrize('path', ["/auth/user"])
def test_login_required_post(client, path):
    with client:
        response = client.post(path)
        assert response.status_code == 401
