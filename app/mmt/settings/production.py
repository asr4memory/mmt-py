import logging
import os

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

# SSL config. This supposes a reverse proxy is used for HTTPS.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Request profiling with django-silk, switched on per deployment. Only staff
# users can open /silk/.
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
