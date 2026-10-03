import logging
import os
import re

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from .base import *

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

# Request profiling with django-silk, switched on per deployment with
# SILK_ENABLED. Only staff users can open /silk/.
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

# Error tracking
sentry_url = os.environ.get('SENTRY_URL')
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
