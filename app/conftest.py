import os

os.environ.setdefault('DJANGO_ENV', 'test')

import pytest
from django.conf import settings
from django.test import override_settings


@pytest.fixture(autouse=True, scope='session')
def apply_test_settings():
    # Session scope is required because Django's setUpTestData runs at class
    # level, before function-scoped fixtures apply. Once all tests are converted
    # to pytest style (no more TestCase subclasses), this can be replaced with
    # a function-scoped fixture using pytest-django's `settings` fixture.
    # The values cannot be moved into settings.py under `if DJANGO_ENV ==
    # 'test'`: pytest-django imports the settings module before this file runs,
    # so DJANGO_ENV is still 'development' at that point and such a branch is
    # never taken.
    with override_settings(
        # The default PBKDF2 hasher runs over a million iterations per hash,
        # which dominates the suite: every user creation and every login pays
        # for it. The hashes in test_data.json are MD5 hashes as well, so no
        # other hasher has to stay in the list.
        PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
        PAGINATION_COUNT=10,
        MMT_ASR_ENABLED=True,
        MMT_INTERNAL_DOMAINS=['fu-berlin.de', 'example.com'],
        MMT_USER_FILES_DIR=settings.BASE_DIR / 'user_files_test',
    ):
        yield
