from datetime import datetime

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
