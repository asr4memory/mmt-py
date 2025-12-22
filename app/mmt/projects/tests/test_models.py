import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from mmt.projects.models import Project

User = get_user_model()


class ProjectModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )
        cls.project = Project.objects.create(user=cls.bob, title='Test project')

        # Remove project directory if it exists.
        shutil.rmtree(cls.project.project_directory, ignore_errors=True)

    def test_project_directory(self):
        """Returns project directory path."""
        date_now = timezone.now()
        project = self.project

        actual = project.project_directory
        expected = (
            settings.MMT_USER_FILES_DIR
            / 'bob'
            / ('test_project' + date_now.strftime('.%Y%m%d%H%M%S'))
        )
        self.assertEqual(actual, expected)

    def test_upload_directory(self):
        """Returns upload directory path."""
        actual = self.project.upload_directory
        expected = self.project.project_directory / 'upload'
        self.assertEqual(actual, expected)

    def test_download_directory(self):
        """Returns download directory path."""
        actual = self.project.download_directory
        expected = self.project.project_directory / 'download'
        self.assertEqual(actual, expected)

    def test_make_and_remove_directories(self):
        """Makes and removes directories in the filesystem."""
        result = self.project.remove_project_directories()
        self.assertFalse(result, 'Directory did not exist, tried to delete it')

        project_directory = self.project.make_project_directories()
        upload_directory = project_directory / 'upload'
        download_directory = project_directory / 'download'
        self.assertTrue(project_directory.exists(), 'Project directory was created.')
        self.assertTrue(upload_directory.exists(), 'Upload directory was created.')
        self.assertTrue(download_directory.exists(), 'Download directory was created.')

        project_directory = self.project.make_project_directories()
        self.assertTrue(
            project_directory.exists(),
            'Idempotent. Does not raise if directory existed.',
        )

        result = self.project.remove_project_directories()
        self.assertTrue(result, 'Directory did exist and was deleted.')

        self.assertFalse(
            project_directory.exists(), 'Directory does not exist anymore.'
        )
