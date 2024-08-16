from flask import Blueprint, g, jsonify, request

from mmt_backend.auth import login_required, admin_required
from mmt_backend.db import get_db


bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/users", methods=["GET"])
@login_required
@admin_required
def index():
    user_id = g.user["id"]
    db = get_db()
    user_result = db.execute(
        "SELECT id, username, email, locale, admin, activated, can_upload"
        " FROM user"
        " ORDER BY username ASC"
    ).fetchall()
    user_list = [
        {
            "id": user_row["id"],
            "username": user_row["username"],
            "email": user_row["email"],
            "locale": user_row["locale"],
            "admin": bool(user_row["admin"]),
            "activated": bool(user_row["activated"]),
            "can_upload": bool(user_row["can_upload"]),
        }
        for user_row in user_result
    ]
    return jsonify(user_list), 200
