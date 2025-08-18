from http.client import FOUND

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from mmt.projects.models import Project

User = get_user_model()


class ProjectViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_superuser(
            username="alice", password="password", email="alice@example.com"
        )
        cls.bob = User.objects.create_user(
            username="bob", password="password", email="bob@example.com"
        )
        cls.project = Project.objects.create(user=cls.alice, name="Test project")

        perm = Permission.objects.get(codename="view_project")
        cls.bob.user_permissions.add(perm)


    def test_project_detail_page(self):
        """Project detail page renders correctly."""
        self.client.login(username="alice", password="password")
        project = Project.objects.first()

        response = self.client.get(f"/projects/{project.id}/")
        soup = BeautifulSoup(response.content, "html.parser")
        project_name = soup.find(attrs={"data-testid": "project-name"})

        self.assertIn("Test project", project_name.get_text())

    def test_project_page_logged_out(self):
        """Redirects if user is not logged in."""
        project = Project.objects.first()
        response = self.client.get(f"/projects/{project.id}/")
        self.assertEqual(response.status_code, FOUND)

    def test_project_detail_page_another_user(self):
        """Project detail page of another user is not visible."""
        self.client.login(username="bob", password="password")
        project = Project.objects.first()

        response = self.client.get(f"/projects/{project.id}/")
        self.assertEqual(response.status_code, 404)
