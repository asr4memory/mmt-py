import os
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from mmt.projects.models import ProcessingRequest, Project

User = get_user_model()


def remove_path(path):
    """Remove path whether it is a file or a directory; ignore if missing.

    ``shutil.rmtree`` cannot remove a plain file (it raises NotADirectoryError,
    swallowed by ignore_errors), so a leftover file would persist across tests.
    """
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


class ProjectModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )
        cls.project = Project.objects.create(user=cls.bob, title='Test project')

        # Remove project directory if it exists.
        remove_path(cls.project.project_directory)

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


class EnsureDirectoriesTests(TestCase):
    def setUp(self):
        self.bob = User.objects.create_user(
            username='bob_ensure', password='password', email='bob_ensure@example.com'
        )
        self.project = Project.objects.create(user=self.bob, title='Test project')
        remove_path(self.project.project_directory)
        self.addCleanup(remove_path, self.project.project_directory)

    def test_creates_directories(self):
        """Creates the project, upload and download directories."""
        self.project.ensure_directories()

        self.assertTrue(self.project.project_directory.is_dir())
        self.assertTrue(self.project.upload_directory.is_dir())
        self.assertTrue(self.project.download_directory.is_dir())

    def test_idempotent(self):
        """Calling twice does not raise when directories already exist."""
        self.project.ensure_directories()
        self.project.ensure_directories()

        self.assertTrue(self.project.upload_directory.is_dir())


class CheckDirectoriesTests(TestCase):
    def setUp(self):
        self.bob = User.objects.create_user(
            username='bob_check', password='password', email='bob_check@example.com'
        )
        self.project = Project.objects.create(user=self.bob, title='Test project')
        remove_path(self.project.project_directory)
        self.addCleanup(remove_path, self.project.project_directory)

    def test_ok_when_all_present(self):
        """No issues when all directories exist and are usable."""
        self.project.ensure_directories()

        result = self.project.check_directories()

        self.assertTrue(result.ok)
        self.assertEqual(result.issues, [])

    def test_missing_directories(self):
        """Reports a missing issue for each required directory."""
        result = self.project.check_directories()

        self.assertFalse(result.ok)
        self.assertEqual(
            {(issue.directory, issue.code) for issue in result.issues},
            {('project', 'missing'), ('upload', 'missing'), ('download', 'missing')},
        )

    def test_not_a_directory(self):
        """Reports not_a_directory when the project path is a file."""
        self.project.project_directory.parent.mkdir(parents=True, exist_ok=True)
        self.project.project_directory.write_bytes(b'not a dir')

        result = self.project.check_directories()

        project_issues = [i for i in result.issues if i.directory == 'project']
        self.assertEqual([i.code for i in project_issues], ['not_a_directory'])

    def test_not_writable(self):
        """Reports not_writable when a directory lacks write permission."""
        if os.geteuid() == 0:
            self.skipTest('running as root bypasses permission checks')

        self.project.ensure_directories()
        self.project.upload_directory.chmod(0o500)
        self.addCleanup(self.project.upload_directory.chmod, 0o700)

        result = self.project.check_directories()

        upload_issues = [i for i in result.issues if i.directory == 'upload']
        self.assertEqual([i.code for i in upload_issues], ['not_writable'])


class ProcessingRequestModelTests(TestCase):
    def test_deletable(self):
        """Is deletable unless the status is 'accepted'."""
        processing_request = ProcessingRequest()

        for status in [
            ProcessingRequest.Status.CREATED,
            ProcessingRequest.Status.REJECTED,
            ProcessingRequest.Status.COMPLETED,
        ]:
            processing_request.status = status
            self.assertTrue(processing_request.deletable)

        processing_request.status = ProcessingRequest.Status.ACCEPTED
        self.assertFalse(processing_request.deletable)
