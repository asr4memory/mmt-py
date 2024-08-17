import os
from pathlib import Path

from flask import Flask, json, jsonify
from flask_cors import CORS
from werkzeug.exceptions import (
    HTTPException,
    BadRequest,
    Unauthorized,
    Forbidden,
    NotFound,
    InternalServerError,
)

from .mail import mail, send_test_email
from . import admin
from . import auth
from . import db
from . import downloads
from . import uploads


def create_app(test_config=None):
    # create and configure the app
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder="app",
        static_url_path="/app",
    )
    root_path = Path(__file__).parent.parent
    app_root_path = Path(app.root_path)
    app.config.from_pyfile(app_root_path / "default_config.py")
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=os.path.join(app.instance_path, "mmt_backend.sqlite"),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py")
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # ensure the user_files folder exists
    user_files_path = root_path / "user_files"
    if user_files_path.exists():
        if not user_files_path.is_dir():
            print("user_files exists, but is not a directory!")
    else:
        print("Creating user_files directory...")
        os.mkdir(root_path / "user_files")

    CORS(
        app,
        origins="http://localhost:5173",
        supports_credentials=True,
    )

    mail.init_app(app)

    @app.route("/heartbeat")
    def heartbeat():
        return jsonify({"status": "healthy"})

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return app.send_static_file("index.html")

    db.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(uploads.bp)
    app.register_blueprint(downloads.bp)
    app.register_blueprint(admin.bp)

    @app.errorhandler(BadRequest)
    def resource_not_found(e):
        return jsonify(error=str(e)), 400

    @app.errorhandler(Unauthorized)
    def resource_not_found(e):
        return jsonify(error=str(e)), 401

    @app.errorhandler(Forbidden)
    def resource_not_found(e):
        return jsonify(error=str(e)), 403

    @app.errorhandler(NotFound)
    def resource_not_found(e):
        return jsonify(error=str(e)), 404

    @app.errorhandler(InternalServerError)
    def resource_not_found(e):
        return jsonify(error=str(e)), 500

    @app.errorhandler(HTTPException)
    def handle_exception(e):
        """
        Return JSON instead of HTML for HTTP errors.
        See https://flask.palletsprojects.com/en/3.0.x/errorhandling/
        """
        # start with the correct headers and status code from the error
        response = e.get_response()
        # replace the body with JSON
        response.data = json.dumps(
            {
                "code": e.code,
                "name": e.name,
                "description": e.description,
            }
        )
        response.content_type = "application/json"
        return response

    return app
