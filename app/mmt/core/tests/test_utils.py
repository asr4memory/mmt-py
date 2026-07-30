from django.test import TestCase

from mmt.core.utils import file_category, filename_safe, generate_file_md5


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


def test_file_category_video():
    assert file_category('video/mp4') == 'video'


def test_file_category_video_for_application_ogg():
    assert file_category('application/ogg') == 'video'


def test_file_category_audio():
    assert file_category('audio/mpeg') == 'audio'


def test_file_category_pdf():
    assert file_category('application/pdf') == 'pdf'


def test_file_category_image():
    assert file_category('image/png') == 'image'


def test_file_category_text():
    assert file_category('text/plain') == 'text'


def test_file_category_falls_back_to_media_type():
    """An unrecognised type keeps its media type so no information is lost."""
    assert file_category('application/zip') == 'application/zip'


def test_generate_file_md5(tmp_path):
    path = tmp_path / 'tempfile.mp4'
    path.write_text('Just some dummy text.')

    assert generate_file_md5(path) == 'd9b0cfba497e24f5f842b634f625e41c'
