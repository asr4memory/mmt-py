from bs4 import BeautifulSoup
from django.test import TestCase

from mmt.projects.models import Project


class ProjectViewTests(TestCase):
    fixtures = ["test_data.json"]

    def test_primary_menu_logged_in(self):
        """Project detail page works."""
        self.client.login(username="alice", password="password")
        project = Project.objects.first()

        response = self.client.get(f"/projects/{project.id}/")
        soup = BeautifulSoup(response.content, "html.parser")
        project_name = soup.find(attrs={"data-testid": "project-name"})

        self.assertIn("Test project", project_name.get_text())
