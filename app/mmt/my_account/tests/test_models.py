from pathlib import Path
import shutil
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username="bob", password="password", email="bob@example.com"
        )

        # Remove user directory if it exists.
        shutil.rmtree(cls.bob.user_directory, ignore_errors=True)

    def test_user_directory(self):
        """Returns user directory path."""
        actual = self.bob.user_directory
        expected = settings.MMT_USER_FILES_DIR / "bob"
        self.assertEqual(actual, expected)

    def test_make_and_remove_user_directory(self):
        """Creates and removes the user directory in the file system."""
        self.bob.make_user_directory()
        self.assertTrue(self.bob.user_directory.exists())

        self.bob.remove_user_directory()
        self.assertFalse(self.bob.user_directory.exists())
