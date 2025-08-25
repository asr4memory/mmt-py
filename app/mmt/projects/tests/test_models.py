from datetime import datetime
import shutil

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

    def test_normal_directory_name(self):
        """Directory names are created from title and creation date"""
        date_now = datetime.now()
        project = Project.objects.create(name="Test project", user=self.bob)

        actual = project.directory_name
        expected = "Test_project" + date_now.strftime(".%Y-%m-%dT%H%M%SZ")
        self.assertEqual(actual, expected)

    def test_unsafe_directory_name(self):
        """Directory names are made safe"""
        date_now = datetime.now()
        project = Project.objects.create(name="ä/#*hello", user=self.bob)

        actual = project.directory_name
        expected = "ähello" + date_now.strftime(".%Y-%m-%dT%H%M%SZ")
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
