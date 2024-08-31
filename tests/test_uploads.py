import pytest
from mmt_backend.db import get_db, Upload


def test_index(client, auth):
    auth.login()
    response = client.get("/api/uploads/")
    assert response.status_code == 200
    assert response.json == [
        {
            "id": 1,
            "filename": "testfile.mp4",
            "content_type": "video/mp4",
            "size": 5_000_000,
            "state": "created",
            "created": "Mon, 01 Jan 2024 00:00:00 GMT",
            "checksum_client": "",
            "checksum_server": "",
        }
    ]


def test_create(client, auth):
    auth.login()
    response = client.post(
        "/api/uploads/create",
        json={"filename": "test.mp4", "content_type": "video/mp4", "size": 450_000},
    )
    assert response.status_code == 201
    assert response.json == {"id": 2, "filename": "test.mp4"}


@pytest.mark.parametrize(
    ("filename", "content_type", "size", "message"),
    (
        ("", "", "", "Filename is required."),
        ("test.mp4", "", "", "Content_type is required."),
        ("test.mp4", "video/mp4", "", "Size is required."),
    ),
)
def test_create_validate_input(client, auth, filename, content_type, size, message):
    auth.login()
    response = client.post(
        "/api/uploads/create",
        json={"filename": filename, "content_type": content_type, "size": size},
    )
    assert response.status_code == 403
    assert response.json["message"] == message


def test_update(client, auth, app):
    auth.login()
    response = client.post(
        "/api/uploads/1/update",
        json={"checksum_client": "182e6ad2fd34312407ba97343e063a41"},
    )
    assert response.status_code == 200
    assert response.json == {"success": True}

    with app.app_context():
        db = get_db()
        upload = db.get_or_404(Upload, 1)
        assert upload.checksum_client == "182e6ad2fd34312407ba97343e063a41"


def test_delete(client, auth, app):
    auth.login()
    response = client.post("/api/uploads/1/delete")
    assert response.status_code == 200
    assert response.json == {"success": True}

    with app.app_context():
        db = get_db()
        stmt = db.select(Upload).where(Upload.id == 1)
        upload = db.session.execute(stmt).scalar()
        assert upload is None


def test_wrong_user_delete(app, client, auth):
    # change the upload user to another user
    with app.app_context():
        db = get_db()
        stmt = db.select(Upload).where(Upload.id == 1)
        upload = db.session.execute(stmt).scalar()
        upload.user_id = 2
        db.session.commit()

    auth.login()
    # current user can't modify other user's upload
    response = client.post("/api/uploads/1/delete")
    assert response.status_code == 403


@pytest.mark.parametrize("path", ("/api/uploads/",))
def test_login_required_get(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.json == {"message": "Not logged in"}


@pytest.mark.parametrize("path", ("/api/uploads/create", "/api/uploads/1/delete"))
def test_login_required_post(client, path):
    response = client.post(path)
    assert response.status_code == 401
    assert response.json == {"message": "Not logged in"}
