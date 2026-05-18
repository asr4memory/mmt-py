import pytest
from django.conf import settings
from django.test import override_settings


@pytest.fixture(autouse=True, scope='session')
def apply_test_settings():
    # Session scope is required because Django's setUpTestData runs at class
    # level, before function-scoped fixtures apply. Once all tests are converted
    # to pytest style (no more TestCase subclasses), this can be replaced with
    # a function-scoped fixture using pytest-django's `settings` fixture, or
    # the values can be moved into settings.py under `if DJANGO_ENV == 'test'`.
    with override_settings(
        PAGINATION_COUNT=10,
        MMT_INTERNAL_DOMAINS=['fu-berlin.de', 'example.com'],
        MMT_USER_FILES_DIR=settings.BASE_DIR / 'user_files_test',
    ):
        yield
