import functools

from flask import (
    Blueprint,
    g,
    request,
    session,
)
from werkzeug.security import check_password_hash, generate_password_hash

from mmt_backend.db import get_db
from mmt_backend.mail import send_new_user_email
from mmt_backend.filesystem import create_user_directories

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=("POST",))
def register():
    json = request.get_json()
    username = json.get("username", None)
    email = json.get("email", None)
    password = json.get("password", None)
    db = get_db()
    error = None

    if not username:
        error = "Username is required."
    elif not email:
        error = "Email is required."
    elif not password:
        error = "Password is required."

    if error is None:
        try:
            db.execute(
                "INSERT INTO user (username, email, password) VALUES (?, ?, ?)",
                (username, email, generate_password_hash(password)),
            )
            db.commit()
        except db.IntegrityError:
            error = f"User is already registered."
        else:
            # Registration was successful.
            # TODO: Check if username is safe before creating directory.
            create_user_directories(username)
            send_new_user_email(username)
            return {"username": username, "email": email}, 201

    return {"message": error}, 403


@bp.route("/login", methods=("POST",))
def login():
    json = request.get_json()
    username = json.get("username", None)
    password = json.get("password", None)
    db = get_db()
    error = None
    code = None
    user = db.execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()

    if user is None:
        error = "Username and password do not match."
        code = "username_password_mismatch"
    elif not check_password_hash(user["password"], password):
        error = "Username and password do not match."
        code = "username_password_mismatch"
    elif not user["activated"]:
        error = "User has not been activated yet."
        code = "user_not_activated"

    if error is None:
        session.clear()
        session["user_id"] = user["id"]
        return {
            "username": user["username"],
            "email": user["email"],
            "locale": user["locale"],
        }, 200

    return {"message": error, "code": code}, 403


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = (
            get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
        )


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    return {"success": True}, 200


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return {"message": "Not logged in"}, 401

        return view(**kwargs)

    return wrapped_view
