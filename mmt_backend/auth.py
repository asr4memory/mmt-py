import functools

from flask import Blueprint, g, request, session, abort
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

    if not username:
        abort(400, "Username is required.")

    if not email:
        abort(400, "Email is required.")

    if not password:
        abort(400, "Password is required.")

    try:
        db.execute(
            "INSERT INTO user (username, email, password) VALUES (?, ?, ?)",
            (username, email, generate_password_hash(password)),
        )
        db.commit()
    except db.IntegrityError:
        abort(400, "Username or Email is already in use.")
    else:
        # Registration was successful.
        # TODO: Check if username is safe before creating directory.
        create_user_directories(username)

        admins = db.execute("SELECT email FROM user WHERE admin = true").fetchall()
        admin_emails = [admin["email"] for admin in admins]
        send_new_user_email(recipients=admin_emails, user=username)

        return {"username": username, "email": email}, 201


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
            "admin": bool(user["admin"]),
            "can_upload": bool(user["can_upload"]),
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


def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if bool(g.user["admin"]) is False:
            return {"message": "Not authorized"}, 403

        return view(**kwargs)

    return wrapped_view


@bp.route("/user", methods=("GET",))
@login_required
def user():
    return {
        "username": g.user["username"],
        "email": g.user["email"],
        "locale": g.user["locale"],
        "admin": bool(g.user["admin"]),
        "can_upload": bool(g.user["can_upload"]),
    }, 200


@bp.route("/user", methods=("POST",))
@login_required
def user_update():
    json = request.get_json()
    locale = json.get("locale", None)
    db = get_db()

    if locale is None:
        abort(400, description="Locale is required.")
    elif locale not in ["en", "de"]:
        abort(400, description="Locale must be 'en' or 'de'.")

    db.execute(
        "UPDATE user SET locale = ? WHERE id = ?",
        (locale, g.user["id"]),
    )
    db.commit()

    return {
        "username": g.user["username"],
        "email": g.user["email"],
        "locale": locale,
    }, 200
