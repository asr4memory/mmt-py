import logging
import os
import re

import sentry_sdk
from celery.schedules import crontab
from sentry_sdk.integrations.logging import LoggingIntegration

from .base import *

# Settings read from environment variables. All of them have a default.

# Request profiling with django-silk, switched on per deployment. Only staff
# users can open /silk/.
SILK_ENABLED = os.environ.get('SILK_ENABLED') == 'true'
SILKY_INTERCEPT_PERCENT = int(os.environ.get('SILK_INTERCEPT_PERCENT', '10'))

sentry_url = os.environ.get('SENTRY_URL')

MAILERS = {
    'default': {
        'OPTIONS': {
            'host': os.environ.get('EMAIL_HOST', 'localhost'),
            'port': int(os.environ.get('EMAIL_PORT', '25')),
            'username': os.environ.get('EMAIL_HOST_USER', ''),
            'password': os.environ.get('EMAIL_HOST_PASSWORD', ''),
        },
    },
}


MIDDLEWARE = [*MIDDLEWARE]
MIDDLEWARE.insert(
    MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1,
    'whitenoise.middleware.WhiteNoiseMiddleware',
)

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}


def immutable_file_test(path, url):
    # Matches the hashed file names that Vite generates, such as
    # `some_file-CSliV9zW.js`.
    return re.match(r'^.+[.-][0-9a-zA-Z_-]{8,12}\..+$', url)


WHITENOISE_IMMUTABLE_FILE_TEST = immutable_file_test

# HTTPS is terminated by a reverse proxy, which sets X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Request profiling with django-silk
if SILK_ENABLED:
    # Placed after WhiteNoise, so that static files are not recorded.
    MIDDLEWARE.insert(
        MIDDLEWARE.index('django.contrib.sessions.middleware.SessionMiddleware'),
        'silk.middleware.SilkyMiddleware',
    )
    SILKY_AUTHENTICATION = True
    SILKY_AUTHORISATION = True
    SILKY_PYTHON_PROFILER = True
    # Silk does not delete old requests while it handles a request, because
    # two parallel requests that delete the same rows cause a database
    # deadlock. A daily task deletes them instead.
    SILKY_MAX_RECORDED_REQUESTS_CHECK_PERCENT = 0
    CELERY_BEAT_SCHEDULE['delete-old-silk-requests'] = {
        'task': 'mmt.core.tasks.task_delete_old_silk_requests',
        'schedule': crontab(hour=3, minute=0),
    }

# Error tracking
if sentry_url:
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
