from django.contrib.auth import get_user_model
from django.test import TestCase

from mmt.projects.use_cases import create_project

from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


class CheckFileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username='bob_check', password='password', email='bob_check@example.com'
        )
        cls.project = create_project(title='Test project', user=cls.bob)

    def make_file(self, content: bytes, *, has_file: bool = True) -> UploadedFile:
        uploaded_file = UploadedFile.objects.create(
            filename='test_file.mp4',
            original_filename='test_file.mp4',
            media_type='video/mp4',
            project=self.project,
            size=len(content),
            has_file=has_file,
        )
        path = uploaded_file.file_path
        path.write_bytes(content)
        self.addCleanup(path.unlink, missing_ok=True)
        return uploaded_file

    def test_ok_when_file_matches(self):
        """A present, correctly sized file produces no issues."""
        uploaded_file = self.make_file(b'hello world')

        result = uploaded_file.check_file()

        self.assertTrue(result.ok)
        self.assertEqual(result.issues, [])

    def test_missing_file(self):
        """Reports a missing issue when the file is absent."""
        uploaded_file = UploadedFile.objects.create(
            filename='gone.mp4',
            original_filename='gone.mp4',
            media_type='video/mp4',
            project=self.project,
            size=10,
            has_file=True,
        )

        result = uploaded_file.check_file()

        self.assertFalse(result.ok)
        self.assertEqual([issue.code for issue in result.issues], ['missing'])

    def test_size_mismatch(self):
        """Reports a size mismatch when disk size differs from the database."""
        uploaded_file = self.make_file(b'hello world')
        uploaded_file.size = 999

        result = uploaded_file.check_file()

        self.assertEqual([issue.code for issue in result.issues], ['size_mismatch'])

    def test_has_file_mismatch(self):
        """Reports when a file exists on disk but has_file is False."""
        uploaded_file = self.make_file(b'hello world', has_file=False)

        result = uploaded_file.check_file()

        self.assertEqual([issue.code for issue in result.issues], ['has_file_mismatch'])
