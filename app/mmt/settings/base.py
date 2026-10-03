import os
import tomllib
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Variables that are already set in the environment take precedence over the
# values in .env.
load_dotenv(BASE_DIR / '.env')


# Settings read from environment variables. A variable read with
# os.environ[...] is required; the others have a default.

SECRET_KEY = os.environ['SECRET_KEY']
ALLOWED_HOSTS = [h for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h]

# Origins accepted for unsafe requests whose Origin header does not match the
# request host, for example behind a proxy that changes the host or port.
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if o
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ['DATABASE_NAME'],
        'USER': os.environ.get('DATABASE_USER', ''),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', ''),
        'HOST': os.environ.get('DATABASE_HOST', ''),
        'PORT': os.environ.get('DATABASE_PORT', ''),
    },
}

DEFAULT_FROM_EMAIL = os.environ['EMAIL_FROM']

CELERY_BROKER_URL = os.environ['CELERY_BROKER_URL']

OPENID_CONNECT_SERVER_URL = os.environ.get(
    'OPENID_CONNECT_SERVER_URL', 'https://portal.oral-history.digital'
)
OPENID_CONNECT_SECRET = os.environ['OPENID_CONNECT_SECRET']

MMT_USER_FILES_DIR = Path(os.environ.get('USER_FILES_DIR', BASE_DIR / 'user_files'))

MMT_ASR_API_URL = os.environ.get('ASR_API_URL', '')
# The transcription feature is available exactly when an ASR service is
# configured. A deployment without one leaves ASR_API_URL unset.
MMT_ASR_ENABLED = bool(MMT_ASR_API_URL)

MMT_NER_API_URL = os.environ.get('NER_API_URL', 'http://localhost:8001')

# Media files are delegated to nginx via X-Accel-Redirect exactly when this
# names an internal location. An empty value, the default, means the
# application serves the bytes itself.
MMT_X_ACCEL_LOCATION = os.environ.get('X_ACCEL_LOCATION', '')
if MMT_X_ACCEL_LOCATION:
    if not MMT_X_ACCEL_LOCATION.startswith('/'):
        raise ImproperlyConfigured('X_ACCEL_LOCATION must start with a slash')
    if not MMT_X_ACCEL_LOCATION.endswith('/'):
        MMT_X_ACCEL_LOCATION += '/'


# Security

DEBUG = False


# Applications

INSTALLED_APPS = [
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.openid_connect',
    'django_json_widget',
    'django_vite',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'import_export',
    'mmt.core',
    'mmt.my_account',
    'mmt.projects',
    'mmt.transcripts',
    'mmt.uploaded_files',
    'silk',
    'tinymce',
    'widget_tweaks',
]


# Middleware

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'mmt.my_account.middleware.AccountLocaleMiddleware',
    'mmt.my_account.middleware.TermsRedirectMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# URLs and WSGI

ROOT_URLCONF = 'mmt.urls'
WSGI_APPLICATION = 'mmt.wsgi.application'


# Templates

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'mmt' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'mmt.core.context_processors.core_constants',
            ],
        },
    },
]


# Authentication

AUTH_USER_MODEL = 'my_account.User'
LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = 'welcome'
LOGOUT_REDIRECT_URL = 'welcome'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization

USE_I18N = True
LANGUAGES = [
    ('de', _('German')),
    ('en', _('English')),
]
LANGUAGE_CODE = 'en'
LOCALE_PATHS = (BASE_DIR / 'locale',)
FORMAT_MODULE_PATH = 'mmt.formats'
USE_TZ = True
TIME_ZONE = 'Europe/Berlin'


# Static and media files

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'build'
STATICFILES_DIRS = [BASE_DIR / 'static', BASE_DIR / 'vite_assets_dist']

MEDIA_ROOT = MMT_USER_FILES_DIR


# Uploads

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB


# System checks

SILENCED_SYSTEM_CHECKS = [
    'models.W036',
    'staticfiles.W004',
]


# Testing

TEST_RUNNER = 'mmt.tests.runner.MMTTestRunner'


# django-allauth

ACCOUNT_FORMS = {
    'login': 'mmt.my_account.forms.CustomLoginForm',
    'signup': 'mmt.my_account.forms.CustomSignupForm',
    'reset_password': 'mmt.my_account.forms.CustomResetPasswordForm',
    'change_password': 'mmt.my_account.forms.CustomChangePasswordForm',
}
ACCOUNT_VIEWS = {
    'signup': 'mmt.my_account.views.CustomSignUpView',
}
ACCOUNT_SIGNUP_FIELDS = ['username*', 'email*', 'password1*', 'password2*']
ACCOUNT_LOGIN_METHODS = ['username', 'email']
ACCOUNT_CHANGE_EMAIL = True
ACCOUNT_SIGNUP_FORM_HONEYPOT_FIELD = 'address'
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[MMT] '
ACCOUNT_USERNAME_MIN_LENGTH = 4
ACCOUNT_USERNAME_VALIDATORS = 'mmt.my_account.validators.custom_username_validators'
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'

SOCIALACCOUNT_ADAPTER = 'mmt.my_account.adapter.MySocialAccountAdapter'
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_PROVIDERS = {
    'openid_connect': {
        'APPS': [
            {
                'provider_id': 'ohd',
                'name': 'Oral-History.Digital',
                'client_id': 'mmt',
                'secret': OPENID_CONNECT_SECRET,
                'settings': {
                    'server_url': OPENID_CONNECT_SERVER_URL,
                    # The client sends its secret to the token endpoint in an
                    # HTTP Basic authorization header.
                    'token_auth_method': 'client_secret_basic',
                    'oauth_pkce_enabled': False,
                },
            },
        ],
    }
}


# Celery

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Periodic tasks, run by Celery beat. One sweep polls every non-terminal
# transcription job, so the number of tasks does not grow with the number of
# jobs and a missed tick is corrected by the next one.
CELERY_BEAT_SCHEDULE = {
    'sweep-transcription-jobs': {
        'task': 'mmt.transcripts.tasks.task_sweep_transcription_jobs',
        'schedule': 60.0,
    },
}


# Django Vite

DJANGO_VITE = {'default': {'dev_mode': False}}


# django-silk

# The app is always installed, so that its static files are collected at build
# time. Profiling is off unless the production settings switch it on.
SILK_ENABLED = False


# Project settings


def get_project_version() -> str:
    pyproject_toml_file = BASE_DIR / 'pyproject.toml'
    with open(pyproject_toml_file, 'rb') as f:
        data = tomllib.load(f)

    if 'project' in data and 'version' in data['project']:
        version = data['project']['version']
    else:
        version = 'unknown'

    return version


MMT_SITE_HOST = 'https://mmt.oral-history.digital'
MMT_APP_VERSION = get_project_version()
MMT_DETECT_DOWNLOADABLE_FILES = False
MMT_EMAIL_SUBJECT_PREFIX = '[mmt]'
MMT_TERMS_VERSION = 1
MMT_INTERNAL_DOMAINS = ['fu-berlin.de']
MMT_MAX_UPLOAD_SIZE = 10 * 1024**4  # 10 TB
MMT_UPLOAD_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB
MMT_ACCEPTED_FILES = [
    # Media (wildcard)
    'audio/*',
    'image/*',
    'video/*',
    # Documents & data
    'application/json',
    'application/pdf',
    'application/rtf',
    'application/vnd.oasis.opendocument.spreadsheet',
    'application/vnd.oasis.opendocument.text',
    'application/x-subrip',
    'text/csv',
    'text/plain',
    'text/vtt',
    # Container/specialty formats
    'application/mxf',
    'application/ogg',
    'model/vnd.mts',
]
