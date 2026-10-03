from .base import *

DEBUG = True

INSTALLED_APPS = [*INSTALLED_APPS, 'debug_toolbar', 'django_extensions']

MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware', *MIDDLEWARE]

# Needed for debug-toolbar:
INTERNAL_IPS = ['127.0.0.1']

MAILERS = {'default': {'BACKEND': 'django.core.mail.backends.console.EmailBackend'}}

DJANGO_VITE = {'default': {'dev_mode': True}}
