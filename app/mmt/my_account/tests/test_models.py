import shutil
from datetime import UTC, datetime

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, override_settings

from mmt.my_account.models import FeatureFlag

User = get_user_model()


class UserModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username='bob',
            password='password',
            email='bob@example.com',
            terms_accepted_version=1,
        )

        # Remove user directory if it exists.
        shutil.rmtree(cls.bob.user_directory, ignore_errors=True)

    def test_user_directory(self):
        """Returns user directory path."""
        actual = self.bob.user_directory
        expected = settings.MMT_USER_FILES_DIR / 'bob'
        self.assertEqual(actual, expected)

    def test_make_and_remove_user_directory(self):
        """Creates and removes the user directory in the file system."""
        self.bob.make_user_directory()
        self.assertTrue(self.bob.user_directory.exists())

        self.bob.remove_user_directory()
        self.assertFalse(self.bob.user_directory.exists())

    @override_settings(MMT_TERMS_VERSION=1)
    def test_accepted_current_version(self):
        self.assertTrue(self.bob.has_accepted_terms)

    @override_settings(MMT_TERMS_VERSION=1)
    def test_never_accepted(self):
        self.bob.terms_accepted_version = None
        self.assertFalse(self.bob.has_accepted_terms)

    @override_settings(MMT_TERMS_VERSION=2)
    def test_accepted_previous_version_after_bump(self):
        self.assertFalse(self.bob.has_accepted_terms)

    @override_settings(MMT_INTERNAL_DOMAINS=['fu-berlin.de'])
    def test_is_external_user_true(self):
        self.assertTrue(self.bob.is_external_user())

    def test_is_external_user_false(self):
        self.bob.email = 'bob@fu-berlin.de'
        self.assertFalse(self.bob.is_external_user())

    @override_settings(MMT_INTERNAL_DOMAINS=['fu-berlin.de'])
    def test_has_to_agree_to_dpa_true(self):
        self.assertTrue(self.bob.has_to_agree_to_dpa())

    def test_has_to_agree_to_dpa_false(self):
        self.bob.dpa_accepted_at = datetime.now(tz=UTC)
        self.assertFalse(self.bob.has_to_agree_to_dpa())

    def test_has_to_agree_to_dpa_internal(self):
        self.bob.email = 'bob@fu-berlin.de'
        self.assertFalse(self.bob.has_to_agree_to_dpa())


@pytest.fixture
def flag_user(db):
    return User.objects.create_user(
        username='alice',
        password='password',
        email='alice@example.com',
    )


def test_flag_in_enabled_for_all_is_enabled_without_row(flag_user, monkeypatch):
    """A flag listed in ENABLED_FOR_ALL is enabled without a per-user row."""
    monkeypatch.setattr(
        FeatureFlag,
        'ENABLED_FOR_ALL',
        frozenset({FeatureFlag.Name.DUMMY}),
    )

    assert flag_user.is_flag_enabled(FeatureFlag.Name.DUMMY)


def test_flag_not_in_enabled_for_all_requires_row(flag_user, monkeypatch):
    """A flag not listed in ENABLED_FOR_ALL is enabled only through a per-user row."""
    monkeypatch.setattr(FeatureFlag, 'ENABLED_FOR_ALL', frozenset())

    assert not flag_user.is_flag_enabled(FeatureFlag.Name.DUMMY)

    FeatureFlag.objects.create(user=flag_user, name=FeatureFlag.Name.DUMMY)
    assert flag_user.is_flag_enabled(FeatureFlag.Name.DUMMY)


def test_duplicate_flag_raises_integrity_error(flag_user):
    FeatureFlag.objects.create(user=flag_user, name=FeatureFlag.Name.DUMMY)

    with pytest.raises(IntegrityError):
        FeatureFlag.objects.create(
            user=flag_user, name=FeatureFlag.Name.DUMMY
        )
