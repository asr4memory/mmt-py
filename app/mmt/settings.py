from pathlib import Path
import re
import tomllib

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
import environ


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SENTRY_URL=(str, None),
)

environ.Env.read_env(BASE_DIR / ".env")

django_env = env("DJANGO_ENV")
if django_env not in ["development", "production", "test"]:
    raise ImproperlyConfigured(
        "DJANGO_ENV must be one of development, production or test"
    )

DEBUG = env("DEBUG")
SECRET_KEY = env("SECRET_KEY")

allowed_hosts_value = env("ALLOWED_HOSTS", default="")
ALLOWED_HOSTS = env.parse_value(allowed_hosts_value, list)
TEST_RUNNER = "mmt.tests.runner.MMTTestRunner"


# Application definition

INSTALLED_APPS = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.openid_connect",
    "django_htmx",
    "django_vite",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.humanize",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "mmt.core",
    "mmt.downloads",
    "mmt.my_account",
    "mmt.pages",
    "mmt.upload_jobs",
    "mmt.uploaded_files",
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
    "allauth.account.middleware.AccountMiddleware",
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
        "DIRS": [BASE_DIR / "mmt" / "templates"],
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

AUTH_USER_MODEL = "my_account.User"
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "account:profile"
LOGOUT_REDIRECT_URL = "welcome"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

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

ACCOUNT_SIGNUP_FIELDS = ["username*", "email*", "password1*", "password2*"]
ACCOUNT_LOGIN_METHODS = ["username", "email"]
ACCOUNT_SIGNUP_FORM_HONEYPOT_FIELD = "address"
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[MMT] "
ACCOUNT_USERNAME_MIN_LENGTH = 4
ACCOUNT_USERNAME_VALIDATORS = 'mmt.my_account.validators.custom_username_validators'


SOCIALACCOUNT_PROVIDERS = {
    "openid_connect": {
        "APPS": [
            {
                "provider_id": "ohd",
                "name": "Oral History.Digital",
                "client_id": "mmt",
                "secret": "your.service.secret",
                "settings": {
                    "server_url": "http://portal.oral-history.localhost:3000",
                    # "server_url": "https://portal.oral-history.digital",
                    # Optional token endpoint authentication method.
                    # May be one of "client_secret_basic", "client_secret_post"
                    # If omitted, a method from the the server's
                    # token auth methods list is used
                    "token_auth_method": "client_secret_basic",
                    # Optional PKCE defaults to False, but may be required by
                    # your provider
                    "oauth_pkce_enabled": False,
                },
            },
        ],
    }
}


# Internationalization

USE_I18N = True
LANGUAGES = [
    ("de", _("German")),
    ("en", _("English")),
]
LANGUAGE_CODE = "en"
LOCALE_PATHS = (BASE_DIR / "locale",)
USE_TZ = True
TIME_ZONE = "UTC"


# Static files (CSS, JavaScript, Images)

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "build"
STATICFILES_DIRS = [BASE_DIR / "static", BASE_DIR / "vite_assets_dist"]

if django_env == "production":
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }


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
CELERY_BROKER_URL = env("CELERY_BROKER_URL")


# Django Vite asset management

if django_env in ["development", "test"]:
    DJANGO_VITE = {"default": {"dev_mode": True}}


# Whitenoise static files


def immutable_file_test(path, url):
    # Match vite (rollup)-generated hashes, à la, `some_file-CSliV9zW.js`
    return re.match(r"^.+[.-][0-9a-zA-Z_-]{8,12}\..+$", url)


WHITENOISE_IMMUTABLE_FILE_TEST = immutable_file_test


# Error Tracking

sentry_url = env("SENTRY_URL")
if django_env == "production" and sentry_url:
    import sentry_sdk

    sentry_sdk.init(
        dsn=sentry_url,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )


####################
# Project settings #
####################


def get_project_version() -> str:
    pyproject_toml_file = BASE_DIR / "pyproject.toml"
    with open(pyproject_toml_file, "rb") as f:
        data = tomllib.load(f)

    if "project" in data and "version" in data["project"]:
        version = data["project"]["version"]
    else:
        version = "unknown"

    return version


MMT_APP_VERSION = get_project_version()
MMT_USER_FILES_DIR = Path(env("USER_FILES_DIR", default=BASE_DIR / "user_files"))
MMT_DETECT_DOWNLOADABLE_FILES = False
