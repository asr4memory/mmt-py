import hashlib
from pathlib import Path

from flask import Blueprint, g, jsonify, request
from sqlalchemy import desc
from werkzeug.exceptions import abort
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget

from mmt_backend.auth import login_required, get_admin_emails
from mmt_backend.db import get_db, User, Upload
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
    db = get_db()
    upload = db.get_or_404(Upload, id)

    if upload is None:
        abort(404, f"Upload id {id} doesn't exist.")

    if check_user and upload.user_id != g.user.id:
        abort(403)

    return upload


@bp.route("/")
@login_required
def index():
    user_id = g.user.id
    db = get_db()

    stmt = (
        db.select(Upload)
        .where(Upload.user_id == user_id)
        .order_by(desc(Upload.created_at))
    )
    uploads = db.session.execute(stmt).scalars()

    upload_list = [
        {
            "id": upload.id,
            "filename": upload.filename,
            "content_type": upload.content_type,
            "size": upload.size,
            "state": upload.state,
            "created": upload.created_at,
            "checksum_client": upload.checksum_client,
            "checksum_server": upload.checksum_server,
        }
        for upload in uploads
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
    upload = Upload(
        filename=filename, content_type=content_type, size=size, user_id=g.user.id
    )
    db.session.add(upload)
    db.session.commit()

    return {"id": upload.id, "filename": upload.filename}, 201


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
    upload.checksum_client = checksum_server
    db.session.add(upload)
    db.session.commit()

    # Send emails.
    admin_emails = get_admin_emails()
    send_admin_file_uploaded_email(
        recipients=admin_emails,
        username=g.user.username,
        filename=upload.filename,
    )
    send_user_file_uploaded_email(
        to_username=g.user.username,
        to_email=g.user.email,
        filename=upload.filename,
        locale=g.user.locale,
    )

    return {"success": True, "checksum_server": checksum_server}, 200


@bp.route("/<int:upload_id>/update", methods=("POST",))
@login_required
def update(upload_id):
    upload = get_upload(upload_id)
    db = get_db()
    json = request.get_json()
    checksum_client = json.get("checksum_client", None)

    if checksum_client:
        upload.checksum_client = checksum_client
        db.session.add(upload)
        db.session.commit()

    return {"success": True}, 200


@bp.route("/<int:upload_id>/delete", methods=("POST",))
@login_required
def delete(upload_id):
    upload = get_upload(upload_id)
    db = get_db()
    db.session.delete(upload)
    db.session.commit()

    return {"success": True}, 200
