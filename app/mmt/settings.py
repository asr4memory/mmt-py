import re
import tomllib
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    VITE_DEV_MODE=(bool, None),
    SENTRY_URL=(str, None),
    CSRF_TRUSTED_ORIGINS=(list, []),
    OPENID_CONNECT_SERVER_URL=(str, 'https://portal.oral-history.digital'),
    OPENID_CONNECT_SECRET=(str, 'your.service.secret'),
    NER_API_URL=(str, 'http://localhost:8001'),
    ASR_API_URL=(str, 'http://localhost:8002'),
)

environ.Env.read_env(BASE_DIR / '.env')

DJANGO_ENV = env('DJANGO_ENV')
if DJANGO_ENV not in ['development', 'production', 'test']:
    raise ImproperlyConfigured(
        'DJANGO_ENV must be one of development, production or test'
    )

DEBUG = env('DEBUG')
SECRET_KEY = env('SECRET_KEY')

allowed_hosts_value = env('ALLOWED_HOSTS', default='')
ALLOWED_HOSTS = env.parse_value(allowed_hosts_value, list)
TEST_RUNNER = 'mmt.tests.runner.MMTTestRunner'

# Temporarily needed for beta version.
CSRF_TRUSTED_ORIGINS = env('CSRF_TRUSTED_ORIGINS')


# Application definition

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
    'tinymce',
    'widget_tweaks',
]
if DJANGO_ENV == 'development':
    INSTALLED_APPS += [
        'debug_toolbar',
        'django_extensions',
    ]


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
if DJANGO_ENV == 'development':
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

if DJANGO_ENV == 'production':
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')


# Needed for debug-toolbar:
if DJANGO_ENV == 'development':
    INTERNAL_IPS = ['127.0.0.1']


ROOT_URLCONF = 'mmt.urls'

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


WSGI_APPLICATION = 'mmt.wsgi.application'


# Database
DATABASES = {
    'default': env.db(),
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


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

OPENID_CONNECT_SERVER_URL = env('OPENID_CONNECT_SERVER_URL')
OPENID_CONNECT_SECRET = env('OPENID_CONNECT_SECRET')

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
                    # Optional token endpoint authentication method.
                    # May be one of "client_secret_basic", "client_secret_post"
                    # If omitted, a method from the the server's
                    # token auth methods list is used
                    'token_auth_method': 'client_secret_basic',
                    # Optional PKCE defaults to False, but may be required by
                    # your provider
                    'oauth_pkce_enabled': False,
                },
            },
        ],
    }
}


# SSL config. This supposes a reverse proxy is used for HTTPS.
if DJANGO_ENV == 'production':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# Internationalization

USE_I18N = True
LANGUAGES = [
    ('de', _('German')),
    ('en', _('English')),
]
LANGUAGE_CODE = 'en'
LOCALE_PATHS = (BASE_DIR / 'locale',)
USE_TZ = True
TIME_ZONE = 'Europe/Berlin'


# Static files (CSS, JavaScript, Images)

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'build'
STATICFILES_DIRS = [BASE_DIR / 'static', BASE_DIR / 'vite_assets_dist']

if DJANGO_ENV == 'production':
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }


# Email

email_url = env.email_url()
EMAIL_BACKEND = email_url['EMAIL_BACKEND']
EMAIL_FILE_PATH = email_url['EMAIL_FILE_PATH']
EMAIL_HOST = email_url['EMAIL_HOST']
EMAIL_PORT = email_url['EMAIL_PORT']
EMAIL_HOST_USER = email_url['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = email_url['EMAIL_HOST_PASSWORD']

DEFAULT_FROM_EMAIL = env('EMAIL_FROM')


# Other stuff
SILENCED_SYSTEM_CHECKS = [
    'models.W036',
    'staticfiles.W004',
]


########################
# Third party settings #
########################

# Celery Async workers

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_URL = env('CELERY_BROKER_URL')

# Periodic tasks, run by Celery beat. One sweep polls every non-terminal
# transcription job, so the number of tasks does not grow with the number of
# jobs and a missed tick is corrected by the next one.
CELERY_BEAT_SCHEDULE = {
    'sweep-transcription-jobs': {
        'task': 'mmt.transcripts.tasks.sweep_transcription_jobs',
        'schedule': 60.0,
    },
}

# Django Vite asset management

# dev_mode defaults to True for development/test, but can be overridden via
# VITE_DEV_MODE. Setting it to False (with built assets present) makes the
# {% vite_asset %} tag resolve against manifest.json, so the test suite catches
# assets that are missing from vite.config.js's rollup inputs.
vite_dev_mode = env('VITE_DEV_MODE')
if vite_dev_mode is None:
    vite_dev_mode = DJANGO_ENV in ['development', 'test']
DJANGO_VITE = {'default': {'dev_mode': vite_dev_mode}}


# Whitenoise static files


def immutable_file_test(path, url):
    # Match vite (rollup)-generated hashes, à la, `some_file-CSliV9zW.js`
    return re.match(r'^.+[.-][0-9a-zA-Z_-]{8,12}\..+$', url)


WHITENOISE_IMMUTABLE_FILE_TEST = immutable_file_test


# Error Tracking

sentry_url = env('SENTRY_URL')
if sentry_url and DJANGO_ENV != 'test':
    import logging

    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=sentry_url,
        send_default_pii=True,
        traces_sample_rate=0,
        integrations=[
            LoggingIntegration(
                level=logging.WARNING,
                event_level=logging.ERROR,
            ),
        ],
    )


####################
# Project settings #
####################


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
MMT_ASR_API_URL = env('ASR_API_URL')
MMT_NER_API_URL = env('NER_API_URL')
MMT_APP_VERSION = get_project_version()
MMT_USER_FILES_DIR = Path(env('USER_FILES_DIR', default=BASE_DIR / 'user_files'))
MMT_DETECT_DOWNLOADABLE_FILES = False
MMT_EMAIL_SUBJECT_PREFIX = '[mmt]'
MMT_TERMS_VERSION = 1
MMT_INTERNAL_DOMAINS = ['fu-berlin.de']
MMT_MAX_UPLOAD_SIZE = 10 * 1024**4  # 10 TB
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

FILE_UPLOAD_TEMP_DIR = MMT_USER_FILES_DIR / '_tmp'


MEDIA_ROOT = MMT_USER_FILES_DIR


MMT_UPLOAD_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = MMT_UPLOAD_CHUNK_SIZE
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
