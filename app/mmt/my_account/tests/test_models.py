from datetime import datetime, UTC
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from mmt.my_account.models import Profile

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


class ProfileModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='alice',
            password='password',
            email='alice@example.com',
        )

    def setUp(self):
        self.profile = Profile.objects.get_or_create(user=self.user)[0]

    def test_chunked_upload_constant(self):
        self.assertEqual(Profile.CHUNKED_UPLOAD, 'chunked_upload')

    def test_feature_flags_defaults_to_empty_dict(self):
        self.assertEqual(self.profile.feature_flags, {})

    def test_valid_flag_key_passes_validation(self):
        self.profile.feature_flags = {Profile.CHUNKED_UPLOAD: True}
        self.profile.full_clean()  # should not raise

    def test_unknown_flag_key_raises_validation_error(self):
        self.profile.feature_flags = {'unknown_flag': True}
        with self.assertRaises(ValidationError):
            self.profile.full_clean()

    def test_feature_flags_can_enable_a_flag(self):
        self.profile.feature_flags = {Profile.CHUNKED_UPLOAD: True}
        self.profile.save()
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.feature_flags[Profile.CHUNKED_UPLOAD])

    def test_feature_flags_can_disable_a_flag(self):
        self.profile.feature_flags = {Profile.CHUNKED_UPLOAD: False}
        self.profile.save()
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.feature_flags[Profile.CHUNKED_UPLOAD])

    def test_is_flag_enabled_true(self):
        self.profile.feature_flags = {Profile.CHUNKED_UPLOAD: True}
        self.assertTrue(self.profile.is_flag_enabled(Profile.CHUNKED_UPLOAD))

    def test_is_flag_enabled_false(self):
        self.profile.feature_flags = {Profile.CHUNKED_UPLOAD: False}
        self.assertFalse(self.profile.is_flag_enabled(Profile.CHUNKED_UPLOAD))

    def test_is_flag_enabled_missing_key(self):
        self.profile.feature_flags = {}
        self.assertFalse(self.profile.is_flag_enabled(Profile.CHUNKED_UPLOAD))
