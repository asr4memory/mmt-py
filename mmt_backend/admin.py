from flask import Blueprint, jsonify, abort
from sqlalchemy.orm import joinedload

from mmt_backend.auth import login_required, admin_required
from mmt_backend.db import get_db, User, Upload
from mmt_backend.mail import send_user_activation_email


bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/users", methods=["GET"])
@login_required
@admin_required
def index():
    db = get_db()

    stmt = db.select(User).order_by(User.username).options(joinedload(User.uploads))
    users = db.session.execute(stmt).scalars().unique().all()

    user_list = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "locale": user.locale,
            "admin": user.is_admin,
            "activated": user.is_active,
            "can_upload": user.can_upload,
            "upload_count": len(user.uploads),
        }
        for user in users
    ]
    return jsonify(user_list), 200


@bp.route("/users/<int:id>/activate", methods=["POST"])
@login_required
@admin_required
def activate_user(id):
    db = get_db()
    user = db.get_or_404(User, id)

    if user is None:
        abort(404, description="User not found")

    if user.is_active:
        abort(400, description="User already activated")

    user.is_active = True
    db.session.add(user)
    db.session.commit()

    send_user_activation_email(user.username, user.email, locale=user.locale)

    return jsonify({"message": "success"}), 200
