from datetime import datetime, timezone
import mimetypes
import os
from pathlib import Path

from flask import Blueprint, g, jsonify, send_from_directory

from mmt_backend.auth import login_required

mimetypes.init()
bp = Blueprint("downloads", __name__, url_prefix="/downloads")


@bp.route("/")
@login_required
def index():
    username = g.user.username

    root_path = Path(__file__).parent.parent
    downloads_path = root_path / "user_files" / username / "downloads"

    if not downloads_path.is_dir():
        return {
            "message": "Downloads directory does not exist for the user.",
            "code": "no_downloads_directory",
        }, 500

    filepaths = [
        path
        for path in downloads_path.iterdir()
        if path.is_file() and path.name != ".DS_Store"
    ]

    files_with_info = []
    for filepath in filepaths:
        media_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
        statinfo = os.stat(filepath)
        file_info = {
            "filename": filepath.name,
            "type": media_type,
            "size": statinfo.st_size,
            "modified": datetime.fromtimestamp(statinfo.st_mtime, tz=timezone.utc),
        }
        files_with_info.append(file_info)

    return jsonify(files_with_info), 200


@bp.route("/<filename>")
@login_required
def download(filename):
    username = g.user.username
    root_path = Path(__file__).parent.parent
    downloads_path = root_path / "user_files" / username / "downloads"

    # TODO: We should not return JSON here.
    if not downloads_path.is_dir():
        return {
            "message": "Downloads directory does not exist for the user.",
            "code": "no_downloads_directory",
        }, 500

    file_path = downloads_path / filename

    if not file_path.is_file():
        return {"message": "File does not exist."}, 404

    return send_from_directory(downloads_path, filename, as_attachment=True)
