from datetime import datetime
from pathlib import Path
import shutil
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from mmt.projects.models import Project

User = get_user_model()


class ProjectModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username="bob", password="password", email="bob@example.com"
        )
        cls.project = Project.objects.create(user=cls.bob, name="Test project")

        # Remove project directory if it exists.
        shutil.rmtree(cls.project.directory_path, ignore_errors=True)

    @mock.patch.object(User, "upload_path", new_callable=mock.PropertyMock)
    def test_normal_directory_path(self, mock_upload_path):
        """Returns project directory for normal project name."""
        date_now = datetime.now()
        project = Project.objects.create(name="Test project", user=self.bob)

        mock_upload_path.return_value = Path("test")
        actual = project.directory_path
        expected = Path("test/test_project" + date_now.strftime(".%Y-%m-%dT%H%M%SZ"))
        self.assertEqual(actual, expected)

    @mock.patch.object(User, "upload_path", new_callable=mock.PropertyMock)
    def test_special_directory_path(self, mock_upload_path):
        """Returns project directory path for project name with special characters."""
        date_now = datetime.now()
        project = Project.objects.create(name="ä/#* hello", user=self.bob)

        mock_upload_path.return_value = Path("test")
        actual = project.directory_path
        expected = Path("test/a_hello" + date_now.strftime(".%Y-%m-%dT%H%M%SZ"))
        self.assertEqual(actual, expected)

    def test_create_and_delete_directory(self):
        """Creates and deletes project directory"""
        result = self.project.delete_directory()
        self.assertFalse(result, "Directory did not exist, tried to delete it")

        path = self.project.create_directory()
        self.assertTrue(path.exists(), "Directory was created.")

        path = self.project.create_directory()
        self.assertTrue(
            path.exists(), "Idempotent. Does not raise if directory existed."
        )

        result = self.project.delete_directory()
        self.assertTrue(result, "Directory did exist and was deleted.")

        self.assertFalse(path.exists(), "Directory does not exist anymore.")
