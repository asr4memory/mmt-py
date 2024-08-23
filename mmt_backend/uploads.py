import hashlib
from pathlib import Path

from flask import Blueprint, g, jsonify, request
from werkzeug.exceptions import abort
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget

from mmt_backend.auth import login_required
from mmt_backend.db import get_db
from mmt_backend.mail import (
    send_admin_file_uploaded_email,
    send_user_file_uploaded_email,
)


bp = Blueprint("uploads", __name__, url_prefix="/uploads")


def generate_file_md5(path, blocksize=2**20):
    m = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()


def get_upload(id, check_user=True):
    upload = (
        get_db()
        .execute(
            "SELECT up.id, filename, state, created, user_id, username"
            " FROM upload up JOIN user us ON up.user_id = us.id"
            " WHERE up.id = ?",
            (id,),
        )
        .fetchone()
    )

    if upload is None:
        abort(404, f"Upload id {id} doesn't exist.")

    if check_user and upload["user_id"] != g.user["id"]:
        abort(403)

    return upload


@bp.route("/")
@login_required
def index():
    user_id = g.user["id"]
    db = get_db()
    uploads = db.execute(
        "SELECT up.id, filename, content_type, size, state, created, checksum_client, checksum_server"
        " FROM upload up JOIN user us ON up.user_id = us.id"
        " WHERE us.id = ?"
        " ORDER BY created DESC",
        (user_id,),
    ).fetchall()
    upload_list = [
        {
            "id": upload_row["id"],
            "filename": upload_row["filename"],
            "content_type": upload_row["content_type"],
            "size": upload_row["size"],
            "state": upload_row["state"],
            "created": upload_row["created"],
            "checksum_client": upload_row["checksum_client"],
            "checksum_server": upload_row["checksum_server"],
        }
        for upload_row in uploads
    ]
    return jsonify(upload_list), 200


@bp.route("/create", methods=("POST",))
@login_required
def create():
    json = request.get_json()
    filename = json.get("filename", None)
    content_type = json.get("content_type", None)
    size = json.get("size", None)

    error = None

    if not filename:
        error = "Filename is required."
    elif not content_type:
        error = "Content_type is required."
    elif not size:
        error = "Size is required."

    if error is not None:
        return {"message": error}, 403

    db = get_db()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO upload (filename, content_type, size, user_id)"
        " VALUES (?, ?, ?, ?)",
        (filename, content_type, size, g.user["id"]),
    )
    db.commit()
    upload_id = cur.lastrowid

    return {"id": upload_id, "filename": filename}, 201


@bp.route("/<int:id>/upload", methods=("POST",))
@login_required
def upload(id):
    upload = get_upload(id)

    root_path = Path(__file__).parent.parent
    filepath = (
        root_path / "user_files" / g.user["username"] / "uploads" / upload["filename"]
    )
    file_ = FileTarget(str(filepath))

    parser = StreamingFormDataParser(headers=request.headers)
    parser.register("file", file_)

    while True:
        chunk = request.stream.read(32_768)
        if not chunk:
            break
        parser.data_received(chunk)

    # Generate server checksum.
    checksum_server = generate_file_md5(filepath)
    db = get_db()
    db.execute(
        "UPDATE upload SET checksum_server = ? WHERE id = ?",
        (checksum_server, id),
    )
    db.commit()

    # Send emails.
    admins = db.execute("SELECT email FROM user WHERE admin = true").fetchall()
    admin_emails = [admin["email"] for admin in admins]
    send_admin_file_uploaded_email(
        recipients=admin_emails,
        username=g.user["username"],
        filename=upload["filename"],
    )
    send_user_file_uploaded_email(
        to_username=g.user["username"],
        to_email=g.user["email"],
        filename=upload["filename"],
    )

    return {"success": True, "checksum_server": checksum_server}, 200


@bp.route("/<int:upload_id>/update", methods=("POST",))
@login_required
def update(upload_id):
    get_upload(upload_id)
    db = get_db()
    json = request.get_json()
    checksum_client = json.get("checksum_client", None)
    if checksum_client:
        db.execute(
            "UPDATE upload SET checksum_client = ? WHERE id = ?",
            (checksum_client, upload_id),
        )
        db.commit()

    return {"success": True}, 200


@bp.route("/<int:upload_id>/delete", methods=("POST",))
@login_required
def delete(upload_id):
    get_upload(upload_id)
    db = get_db()
    db.execute("DELETE FROM upload WHERE id = ?", (upload_id,))
    db.commit()
    return {"success": True}, 200
