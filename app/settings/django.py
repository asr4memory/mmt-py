import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False)
)

environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env("DEBUG")
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = []
INTERNAL_IPS = []

django_env = env("DJANGO_ENV")
if django_env not in ["development", "production", "test"]:
    raise ImproperlyConfigured("DJANGO_ENV must be one of development, production or test")


# Application definition

INSTALLED_APPS = [
    "account.apps.AccountConfig",
    "core.apps.CoreConfig",
    "django_htmx",
    "django_vite",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.humanize",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "downloads.apps.DownloadsConfig",
    "pages.apps.PagesConfig",
    "upload_jobs.apps.UploadJobsConfig",
    "uploaded_files.apps.UploadedFilesConfig",
    "widget_tweaks",
]
if django_env == "development":
    INSTALLED_APPS += [
        "debug_toolbar",
        "django_extensions",
    ]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]
if django_env == "development":
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

if django_env == "production":
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")



ROOT_URLCONF = "mmt.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mmt.wsgi.application"


# Database
DATABASES = {
    "default": env.db(),
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Authentication

AUTH_USER_MODEL = "account.User"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "account:profile"
LOGOUT_REDIRECT_URL = "welcome"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization

USE_I18N = True
LANGUAGES = [
    ("de", _("German")),
    ("en", _("English")),
]
LANGUAGE_CODE = "en-us"
LOCALE_PATHS = (BASE_DIR / "locale",)
USE_TZ = True
TIME_ZONE = "UTC"


# Static files (CSS, JavaScript, Images)

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "build"
STATICFILES_DIRS = [BASE_DIR / "vite_assets_dist"]

# Email

email_url = env.email_url()
EMAIL_BACKEND = email_url["EMAIL_BACKEND"]
EMAIL_FILE_PATH = email_url["EMAIL_FILE_PATH"]
EMAIL_HOST = email_url["EMAIL_HOST"]
EMAIL_PORT = email_url["EMAIL_PORT"]
EMAIL_HOST_USER = email_url["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = email_url["EMAIL_HOST_PASSWORD"]



########################
# Third party settings #
########################

# Celery Async workers

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True


# Django Vite

if django_env == "development":
    DJANGO_VITE = {"default": {"dev_mode": True}}



####################
# Project settings #
####################

MMT_USER_FILES_DIR = BASE_DIR / "user_files"
