from flask import Blueprint, g, jsonify, request

from mmt_backend.auth import login_required, admin_required
from mmt_backend.db import get_db
from mmt_backend.mail import send_user_activation_email


bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/users", methods=["GET"])
@login_required
@admin_required
def index():
    user_id = g.user["id"]
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
    # TODO: Check if user is already activated.
    db = get_db()
    db.execute(
        "UPDATE user SET activated = true WHERE id = ?",
        (id,),
    )
    db.commit()

    # TODO: Test this.
    # TODO: This should be sent to the user, not to the activator!
    send_user_activation_email(g.user["username"], g.user["email"])

    return jsonify({"message": "success"}), 200
