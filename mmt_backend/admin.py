from flask import Blueprint, jsonify, abort

from mmt_backend.auth import login_required, admin_required
from mmt_backend.db import get_db
from mmt_backend.mail import send_user_activation_email


bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/users", methods=["GET"])
@login_required
@admin_required
def index():
    db = get_db()
    user_result = db.execute(
        "SELECT user.id, username, email, locale, admin, activated, can_upload,"
        " (SELECT COUNT(*) FROM upload WHERE upload.user_id = user.id) as upload_count"
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
            "upload_count": user_row["upload_count"],
        }
        for user_row in user_result
    ]
    return jsonify(user_list), 200


@bp.route("/users/<int:id>/activate", methods=["POST"])
@login_required
@admin_required
def activate_user(id):
    db = get_db()
    user = db.execute("SELECT * FROM user WHERE id = ?", (id,)).fetchone()

    if user is None:
        abort(404, description="User not found")

    if user["activated"]:
        abort(400, description="User already activated")

    db.execute(
        "UPDATE user SET activated = true WHERE id = ?",
        (id,),
    )
    db.commit()

    send_user_activation_email(user["username"], user["email"], locale=user["locale"])

    return jsonify({"message": "success"}), 200
