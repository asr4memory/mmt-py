from http import HTTPStatus

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

        perm1 = Permission.objects.get(codename="view_project")
        perm2 = Permission.objects.get(codename="add_project")
        cls.bob.user_permissions.add(perm1, perm2)

    # Project index
    def test_project_index_page_alice(self):
        """Shows the projects of the user."""
        self.client.login(username="alice", password="password")

        response = self.client.get("/projects/")
        soup = BeautifulSoup(response.content, "html.parser")
        project_card = soup.find(attrs={"data-testid": "project-card"})

        self.assertIn("Test project", project_card.get_text())

    def test_project_index_page_bob(self):
        """Does not show projects of other users."""
        self.client.login(username="bob", password="password")

        response = self.client.get("/projects/")
        soup = BeautifulSoup(response.content, "html.parser")
        project_card = soup.find(attrs={"data-testid": "project-card"})

        self.assertIsNone(project_card)

    def test_project_index_logged_out(self):
        """Project index redirects if not logged in."""
        response = self.client.get("/projects/")

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        (self.assertIn("/accounts/login/", response.headers.get("location")),)

    # Project detail
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

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        (self.assertIn("/accounts/login/", response.headers.get("location")),)

    def test_project_detail_page_another_user(self):
        """Project detail page of another user is not visible."""
        self.client.login(username="bob", password="password")
        project = Project.objects.first()

        response = self.client.get(f"/projects/{project.id}/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Project edit
    def test_project_edit_page(self):
        """Project edit page renders correctly."""
        self.client.login(username="bob", password="password")
        response = self.client.get("/projects/create/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.find(attrs={"data-testid": "create-project-form"})
        self.assertIsNotNone(form)

    def test_project_edit_page_redirect(self):
        """Project edit page redirects if not logged in."""
        response = self.client.get("/projects/create/")

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        (self.assertIn("/accounts/login/", response.headers.get("location")),)
