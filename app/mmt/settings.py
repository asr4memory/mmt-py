import os
import re
import tomllib
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Variables that are already set in the environment take precedence over the
# values in .env.
load_dotenv(BASE_DIR / '.env')

DJANGO_ENV = os.environ['DJANGO_ENV']
if DJANGO_ENV not in ['development', 'production', 'test']:
    raise ImproperlyConfigured(
        'DJANGO_ENV must be one of development, production or test'
    )

DEBUG = DJANGO_ENV == 'development'
SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = [h for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h]
TEST_RUNNER = 'mmt.tests.runner.MMTTestRunner'

# Temporarily needed for beta version.
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if o
]


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
    'silk',
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

# Request profiling with django-silk, switched on per deployment. The app is
# always installed so that its static files are collected at build time. Only
# staff users can open /silk/.
SILK_ENABLED = os.environ.get('SILK_ENABLED') == 'true'
if SILK_ENABLED:
    # Placed after WhiteNoise, so that static files are not recorded.
    MIDDLEWARE.insert(
        MIDDLEWARE.index('django.contrib.sessions.middleware.SessionMiddleware'),
        'silk.middleware.SilkyMiddleware',
    )
    SILKY_AUTHENTICATION = True
    SILKY_AUTHORISATION = True
    SILKY_INTERCEPT_PERCENT = int(os.environ.get('SILK_INTERCEPT_PERCENT', '10'))
    SILKY_PYTHON_PROFILER = True


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
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ['DATABASE_NAME'],
        'USER': os.environ.get('DATABASE_USER', ''),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', ''),
        'HOST': os.environ.get('DATABASE_HOST', ''),
        'PORT': os.environ.get('DATABASE_PORT', ''),
    },
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

OPENID_CONNECT_SERVER_URL = os.environ.get(
    'OPENID_CONNECT_SERVER_URL', 'https://portal.oral-history.digital'
)
OPENID_CONNECT_SECRET = os.environ.get('OPENID_CONNECT_SECRET', 'your.service.secret')

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
FORMAT_MODULE_PATH = 'mmt.formats'
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

if DJANGO_ENV == 'development':
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '25'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

DEFAULT_FROM_EMAIL = os.environ['EMAIL_FROM']


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
CELERY_BROKER_URL = os.environ['CELERY_BROKER_URL']

# Periodic tasks, run by Celery beat. One sweep polls every non-terminal
# transcription job, so the number of tasks does not grow with the number of
# jobs and a missed tick is corrected by the next one.
CELERY_BEAT_SCHEDULE = {
    'sweep-transcription-jobs': {
        'task': 'mmt.transcripts.tasks.task_sweep_transcription_jobs',
        'schedule': 60.0,
    },
}

# Django Vite asset management

# dev_mode defaults to True for development/test, but can be overridden via
# VITE_DEV_MODE. Setting it to False (with built assets present) makes the
# {% vite_asset %} tag resolve against manifest.json, so the test suite catches
# assets that are missing from vite.config.js's rollup inputs.
if 'VITE_DEV_MODE' in os.environ:
    vite_dev_mode = os.environ['VITE_DEV_MODE'] == 'true'
else:
    vite_dev_mode = DJANGO_ENV in ['development', 'test']
DJANGO_VITE = {'default': {'dev_mode': vite_dev_mode}}


# Whitenoise static files


def immutable_file_test(path, url):
    # Match vite (rollup)-generated hashes, à la, `some_file-CSliV9zW.js`
    return re.match(r'^.+[.-][0-9a-zA-Z_-]{8,12}\..+$', url)


WHITENOISE_IMMUTABLE_FILE_TEST = immutable_file_test


# Error Tracking

sentry_url = os.environ.get('SENTRY_URL')
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
MMT_ASR_API_URL = os.environ.get('ASR_API_URL', '')
# The transcription feature is available exactly when an ASR service is
# configured. A deployment without one leaves ASR_API_URL unset.
MMT_ASR_ENABLED = bool(MMT_ASR_API_URL)
MMT_NER_API_URL = os.environ.get('NER_API_URL', 'http://localhost:8001')
MMT_APP_VERSION = get_project_version()
MMT_USER_FILES_DIR = Path(os.environ.get('USER_FILES_DIR', BASE_DIR / 'user_files'))
# Media files are delegated to nginx via X-Accel-Redirect exactly when this
# names an internal location. An empty value, the default, means the
# application serves the bytes itself.
MMT_X_ACCEL_LOCATION = os.environ.get('X_ACCEL_LOCATION', '')
if MMT_X_ACCEL_LOCATION:
    if not MMT_X_ACCEL_LOCATION.startswith('/'):
        raise ImproperlyConfigured('X_ACCEL_LOCATION must start with a slash')
    if not MMT_X_ACCEL_LOCATION.endswith('/'):
        MMT_X_ACCEL_LOCATION += '/'
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

MEDIA_ROOT = MMT_USER_FILES_DIR


MMT_UPLOAD_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
