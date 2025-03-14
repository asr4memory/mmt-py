import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "django-insecure-v&me14sv4_mbo_s9xi_r^@f)h7#8v*&6&gp+y2#jp7)5vfl64&"

ALLOWED_HOSTS = []
INTERNAL_IPS = []


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
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "mmt",
        "USER": "root",
        "PASSWORD": "password",
        "OPTIONS": {
            "isolation_level": "read committed",
        },
    }
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


# Celery Async workers

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
