from datetime import datetime, UTC
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from mmt.my_account.models import FeatureFlag, Profile

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


class FeatureFlagModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='alice',
            password='password',
            email='alice@example.com',
        )

    def test_is_flag_enabled_true(self):
        FeatureFlag.objects.create(user=self.user, name=FeatureFlag.Name.CHUNKED_UPLOAD)
        self.assertTrue(self.user.is_flag_enabled(FeatureFlag.Name.CHUNKED_UPLOAD))

    def test_is_flag_enabled_false(self):
        self.assertFalse(self.user.is_flag_enabled(FeatureFlag.Name.CHUNKED_UPLOAD))

    def test_duplicate_flag_raises_integrity_error(self):
        FeatureFlag.objects.create(user=self.user, name=FeatureFlag.Name.CHUNKED_UPLOAD)
        with self.assertRaises(Exception):
            FeatureFlag.objects.create(
                user=self.user, name=FeatureFlag.Name.CHUNKED_UPLOAD
            )
