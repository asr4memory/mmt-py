import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from mmt.projects.models import ProcessingRequest, Project

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
