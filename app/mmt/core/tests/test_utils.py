from django.test import TestCase

from mmt.core.utils import filename_safe


class CoreUtilsTests(TestCase):
    def test_filename_safe(self):
        """Returns safe filename for normal project name."""
        actual = filename_safe('Test project')
        expected = 'test_project'
        self.assertEqual(actual, expected)

    def test_filename_safe_special(self):
        """Returns safe filename for project name with special characters."""
        actual = filename_safe('ä/#* hello')
        expected = 'a_hello'
        self.assertEqual(actual, expected)

    def test_filename_safe_dots(self):
        """Strips leading and trailing dots to prevent path traversal."""
        self.assertRaises(ValueError, filename_safe, '..')
        self.assertRaises(ValueError, filename_safe, '...')
        self.assertEqual(filename_safe('.hidden'), 'hidden')
        self.assertEqual(filename_safe('hello.world'), 'hello.world')

    def test_filename_safe_empty(self):
        """Raises ValueError when input produces an empty string."""
        self.assertRaises(ValueError, filename_safe, '###')
        self.assertRaises(ValueError, filename_safe, '')
