from django.test import TestCase

from mmt.core.utils import filename_safe


class CoreUtilsTests(TestCase):
    def test_filename_safe(self):
        """Returns safe filename for normal project name."""
        actual = filename_safe("Test project")
        expected = "test_project"
        self.assertEqual(actual, expected)

    def test_filename_safe_special(self):
        """Returns safe filename for project name with special characters."""
        actual = filename_safe("ä/#* hello")
        expected = "a_hello"
        self.assertEqual(actual, expected)
