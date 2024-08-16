import os
from pathlib import Path

from flask import Flask
from flask_cors import CORS

from .mail import mail, send_test_email


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
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

    # a simple page that says hello
    @app.route("/hello")
    def hello():
        return f"Hello, World!"

    from . import db

    db.init_app(app)

    from . import auth

    app.register_blueprint(auth.bp)

    from . import uploads

    app.register_blueprint(uploads.bp)
    # app.add_url_rule("/", endpoint="index")

    from . import downloads

    app.register_blueprint(downloads.bp)

    from . import admin

    app.register_blueprint(admin.bp)

    return app
