from pathlib import Path
import tempfile

from django.test import TestCase

from mmt.uploaded_files.utils import generate_file_md5


class UploadedFilesUtilsTests(TestCase):
    def test_generate_file_md5(self):
        dummy_file_path = Path(tempfile.gettempdir()) / "tempfile.mp4"
        with open(dummy_file_path, "w") as f:
            f.write("Just some dummy text.")

        actual = generate_file_md5(dummy_file_path)
        expected = 'd9b0cfba497e24f5f842b634f625e41c'
        self.assertEqual(actual, expected)
