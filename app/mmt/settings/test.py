import os

from .base import *

# Settings read from environment variables. All of them have a default.

# CI sets VITE_DEV_MODE=false, with built assets present. The {% vite_asset %}
# tag then resolves against manifest.json, so the suite catches assets that are
# missing from vite.config.js's rollup inputs.
DJANGO_VITE = {'default': {'dev_mode': os.environ.get('VITE_DEV_MODE') != 'false'}}


# The default PBKDF2 hasher runs over a million iterations per hash, which
# dominates the suite: every user creation and every login pays for it. The
# hashes in test_data.json are MD5 hashes as well, so no other hasher has to
# stay in the list.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

MMT_ASR_ENABLED = True
MMT_INTERNAL_DOMAINS = ['fu-berlin.de', 'example.com']
MMT_USER_FILES_DIR = BASE_DIR / 'user_files_test'
