from http import HTTPStatus
from unittest import mock

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.base import Message
from django.contrib.messages.test import MessagesTestMixin
from django.test import TestCase

from mmt.projects.models import Project
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


class ProjectViewTests(TestCase, MessagesTestMixin):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username="alice", password="password", email="alice@example.com"
        )
        cls.bob = User.objects.create_user(
            username="bob", password="password", email="bob@example.com"
        )
        cls.project = Project.objects.create(user=cls.alice, name="Test project")
        cls.uploaded_file = UploadedFile.objects.create(
            project=cls.project,
            filename="test_file.mp4",
            size=20000,
            transferred=20000,
            media_type="video/mp4",
            status=UploadedFile.UploadStatus.COMPLETE,
        )

        perm1 = Permission.objects.get(codename="view_project")
        perm2 = Permission.objects.get(codename="add_project")
        perm3 = Permission.objects.get(codename="change_project")
        perm4 = Permission.objects.get(codename="delete_project")
        perm5 = Permission.objects.get(codename="view_uploadedfile")
        perm6 = Permission.objects.get(codename="add_uploadedfile")
        cls.alice.user_permissions.add(perm1, perm2, perm3, perm4, perm5, perm6)
        cls.bob.user_permissions.add(perm1, perm2, perm3, perm4, perm5, perm6)

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

        self.assertRedirects(response, "/accounts/login/?next=/projects/")

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

        self.assertRedirects(response, f"/accounts/login/?next=/projects/{project.id}/")

    def test_project_detail_page_another_user(self):
        """Project detail page of another user is not visible."""
        self.client.login(username="bob", password="password")
        project = Project.objects.first()

        response = self.client.get(f"/projects/{project.id}/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # New project
    def test_new_project(self):
        """New project page renders correctly."""
        self.client.login(username="bob", password="password")
        response = self.client.get("/projects/create/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.find(attrs={"data-testid": "create-project-form"})
        self.assertIsNotNone(form)

    def test_new_project_redirect(self):
        """New project page redirects if not logged in."""
        response = self.client.get("/projects/create/")

        self.assertRedirects(response, "/accounts/login/?next=/projects/create/")

    @mock.patch.object(Project, "create_directory")
    def test_new_project_post_request(self, mock_create_directory):
        """New project is created."""
        self.client.login(username="bob", password="password")

        response = self.client.post(
            "/projects/create/",
            {"name": "Bob's project", "description": "Test description"},
        )

        project = Project.objects.get(user=self.bob)
        self.assertRedirects(response, f"/projects/{project.id}/")
        self.assertEqual(project.name, "Bob's project")
        self.assertEqual(project.description, "Test description")
        self.assertMessages(
            response, [Message(level=25, message="Project created successfully.")]
        )
        mock_create_directory.assert_called_once()

    def test_new_project_post_redirect(self):
        """New project post request redirects if not logged in."""
        response = self.client.post(
            "/projects/create/",
            {"name": "Bob's project", "description": "Test description"},
        )
        self.assertRedirects(response, "/accounts/login/?next=/projects/create/")

    # Edit project
    def test_edit_project(self):
        """Edit project page renders correctly."""
        self.client.login(username="alice", password="password")
        response = self.client.get(f"/projects/{self.project.id}/edit/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.find(attrs={"data-testid": "edit-project-form"})
        self.assertIsNotNone(form)

    def test_edit_project_redirect(self):
        """Edit project page redirects if not logged in."""
        response = self.client.get(f"/projects/{self.project.id}/edit/")

        self.assertRedirects(
            response, f"/accounts/login/?next=/projects/{self.project.id}/edit/"
        )

    def test_edit_project_other_user(self):
        """Edit project page does not render for another user."""
        self.client.login(username="bob", password="password")
        response = self.client.get(f"/projects/{self.project.id}/edit/")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @mock.patch.object(Project, "rename_directory_from")
    def test_edit_project_post_request(self, rename_directory_from_mock):
        """Edit project is successful."""
        self.client.login(username="alice", password="password")
        response = self.client.post(
            f"/projects/{self.project.id}/edit/",
            {"name": "New name", "description": "New description"},
        )

        project = Project.objects.get(user=self.alice)
        self.assertRedirects(response, f"/projects/{project.id}/")
        self.assertEqual(project.name, "New name")
        self.assertEqual(project.description, "New description")
        self.assertMessages(
            response, [Message(level=25, message="Project updated successfully.")]
        )
        rename_directory_from_mock.assert_called_once()

    def test_edit_project_post_redirect(self):
        """Edit project post request redirects if not logged in."""
        response = self.client.post(
            f"/projects/{self.project.id}/edit/",
            {"name": "New name", "description": "New description"},
        )
        self.assertRedirects(
            response, f"/accounts/login/?next=/projects/{self.project.id}/edit/"
        )

    def test_edit_project_post_other_user(self):
        """Edit project post request does not work for another user."""
        self.client.login(username="bob", password="password")
        response = self.client.post(
            f"/projects/{self.project.id}/edit/",
            {"name": "New name", "description": "New description"},
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Delete project
    @mock.patch.object(Project, "delete_directory")
    def test_delete_project_post_request(self, delete_directory_mock):
        """Delete project is successful."""
        self.client.login(username="alice", password="password")
        response = self.client.post(f"/projects/{self.project.id}/delete/")

        self.assertRedirects(response, "/projects/")
        self.assertEqual(Project.objects.count(), 0)
        self.assertMessages(
            response, [Message(level=25, message="Project deleted successfully.")]
        )
        delete_directory_mock.assert_called_once()

    def test_delete_project_post_redirect(self):
        """Delete project post request redirects if not logged in."""
        response = self.client.post(f"/projects/{self.project.id}/delete/")
        self.assertRedirects(
            response, f"/accounts/login/?next=/projects/{self.project.id}/delete/"
        )

    def test_delete_project_post_other_user(self):
        """Delete project post request does not work for another user."""
        self.client.login(username="bob", password="password")
        response = self.client.post(f"/projects/{self.project.id}/delete/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Uploaded file detail
    def test_uploaded_file_detail_page(self):
        """Uploaded file detail page renders correctly."""
        self.client.login(username="alice", password="password")
        uploaded_file = UploadedFile.objects.first()
        project = uploaded_file.project

        response = self.client.get(f"/projects/{project.id}/file/{uploaded_file.id}/")
        self.assertContains(response, "<h1>test_file.mp4</h1>", html=True)

    def test_uploaded_file_detail_logged_out(self):
        """Uploaded file detail redirects if user is not logged in."""
        uploaded_file = UploadedFile.objects.first()
        project = uploaded_file.project

        response = self.client.get(f"/projects/{project.id}/file/{uploaded_file.id}/")
        self.assertRedirects(
            response,
            f"/accounts/login/?next=/projects/{project.id}/file/{uploaded_file.id}/",
        )

    def test_uploaded_file_detail_another_user(self):
        """Uploaded file detail page of another user is not visible."""
        self.client.login(username="bob", password="password")
        uploaded_file = UploadedFile.objects.first()
        project = uploaded_file.project
        response = self.client.get(f"/projects/{project.id}/file/{uploaded_file.id}/")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Upload files page
    def test_upload_files_page(self):
        """Upload files page renders correctly."""
        self.client.login(username="alice", password="password")

        project = Project.objects.first()
        response = self.client.get(f"/projects/{project.id}/upload/")

        self.assertContains(response, "<h1>Upload Files</h1>", html=True)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.find(attrs={"data-testid": "upload-files-form"})
        self.assertIsNotNone(form)
        project_id_in_form = int(form.attrs["data-project-id"])
        self.assertEqual(project_id_in_form, project.id)

    def test_upload_files_redirect(self):
        """Upload files page redirects if logged out."""
        project = Project.objects.first()
        response = self.client.get(f"/projects/{project.id}/upload/")

        self.assertRedirects(
            response, f"/accounts/login/?next=/projects/{project.id}/upload/"
        )

    def test_upload_files_other_user(self):
        """Upload files page not accessible by another user."""
        self.client.login(username="bob", password="password")
        project = Project.objects.first()
        response = self.client.get(f"/projects/{project.id}/upload/")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
