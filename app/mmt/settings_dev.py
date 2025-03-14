from .settings_base import *

SECRET_KEY = "django-insecure-e#072wzvkw6s0m-z@e(tr1oqqu3vb7yv7-x4fxj^kh32%ag+n4"

DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
INTERNAL_IPS = ["127.0.0.1"]

INSTALLED_APPS += [
    "debug_toolbar",
    "django_extensions",
]

MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")


DJANGO_VITE = {"default": {"dev_mode": True}}

EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = BASE_DIR / "dev_emails"

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", default="redis://localhost")
