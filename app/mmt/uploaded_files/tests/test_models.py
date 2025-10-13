from pathlib import Path
import shutil
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from mmt.projects.models import Project
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


class UploadedFileModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username="bob", password="password", email="bob@example.com"
        )
        cls.project = Project.objects.create(user=cls.bob, title="Test project")
        cls.uploaded_file = UploadedFile.objects.create(
            filename="test_file.mp4", project=cls.project
        )

        # Remove project directory if it exists.
        shutil.rmtree(cls.project.project_directory, ignore_errors=True)

    @mock.patch.object(Project, "upload_directory", new_callable=mock.PropertyMock)
    def test_file_path(self, mock_project_upload_directory):
        """Returns project directory combined with filename."""
        mock_project_upload_directory.return_value = Path("test")

        actual = self.uploaded_file.file_path
        expected = Path("test/test_file.mp4")
        self.assertEqual(actual, expected)

    def test_delete_file(self):
        """Deletes uploaded file."""
        project = self.project
        uploaded_file = self.uploaded_file
        project.make_project_directories()

        # Create file before it is deleted
        file_path = uploaded_file.file_path
        with open(file_path, "w") as f:
            f.write("Just some dummy text.")

        self.assertTrue(file_path.exists())

        uploaded_file.delete_file()
        self.assertFalse(file_path.exists())
