from django.test import TestCase

from mmt.core.utils import filename_safe


class CoreUtilsTests(TestCase):
    def test_normal_directory_path(self):
        """Returns project directory for normal project name."""
        actual = filename_safe("Test project")
        expected = "test_project"
        self.assertEqual(actual, expected)

    def test_special_directory_path(self):
        """Returns project directory path for project name with special characters."""
        actual = filename_safe("ä/#* hello")
        expected = "a_hello"
        self.assertEqual(actual, expected)
