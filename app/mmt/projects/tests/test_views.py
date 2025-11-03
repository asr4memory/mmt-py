from http import HTTPStatus
from unittest import mock

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.base import Message
from django.contrib.messages.test import MessagesTestMixin
from django.test import TestCase

from mmt.projects.models import Project, ProcessingRequest
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
        cls.project = Project.objects.create(user=cls.alice, title="Test project")
        cls.project.make_project_directories()
        cls.uploaded_file = UploadedFile.objects.create(
            project=cls.project,
            filename="test_file.mp4",
            has_file=True,
            size=20000,
            transferred=20000,
            media_type="video/mp4",
        )
        cls.processing_request = ProcessingRequest.objects.create(
            project=cls.project,
            description="Put on platform.",
            make_available_on_platform=True,
        )

        perm1 = Permission.objects.get(codename="view_project")
        perm2 = Permission.objects.get(codename="add_project")
        perm3 = Permission.objects.get(codename="change_project")
        perm4 = Permission.objects.get(codename="delete_project")
        perm5 = Permission.objects.get(codename="view_uploadedfile")
        perm6 = Permission.objects.get(codename="add_uploadedfile")
        perm7 = Permission.objects.get(codename="view_processingrequest")
        perm8 = Permission.objects.get(codename="add_processingrequest")
        cls.alice.user_permissions.add(
            perm1, perm2, perm3, perm4, perm5, perm6, perm7, perm8
        )
        cls.bob.user_permissions.add(
            perm1, perm2, perm3, perm4, perm5, perm6, perm7, perm8
        )

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

    def test_new_project_post_request(self):
        """New project is created."""
        self.client.login(username="bob", password="password")

        response = self.client.post(
            "/projects/create/",
            {"title": "Bob's project", "description": "Test description"},
        )

        project = Project.objects.get(user=self.bob)
        self.assertRedirects(response, f"/projects/{project.id}/")
        self.assertEqual(project.title, "Bob's project")
        self.assertEqual(project.description, "Test description")
        self.assertMessages(
            response, [Message(level=25, message="Project created successfully.")]
        )

    def test_new_project_post_redirect(self):
        """New project post request redirects if not logged in."""
        response = self.client.post(
            "/projects/create/",
            {"title": "Bob's project", "description": "Test description"},
        )
        self.assertRedirects(response, "/accounts/login/?next=/projects/create/")

    # Project settings
    def test_project_settings(self):
        """Project settings page renders correctly."""
        self.client.login(username="alice", password="password")
        response = self.client.get(f"/projects/{self.project.id}/settings/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.find(attrs={"data-testid": "edit-project-form"})
        self.assertIsNotNone(form)

    def test_project_settings_redirect(self):
        """Project settings page redirects if not logged in."""
        response = self.client.get(f"/projects/{self.project.id}/settings/")

        self.assertRedirects(
            response, f"/accounts/login/?next=/projects/{self.project.id}/settings/"
        )

    def test_project_settings_other_user(self):
        """Project settings page does not render for another user."""
        self.client.login(username="bob", password="password")
        response = self.client.get(f"/projects/{self.project.id}/settings/")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_project_settings_post_request(self):
        """Project settings post request is successful."""
        self.client.login(username="alice", password="password")
        response = self.client.post(
            f"/projects/{self.project.id}/settings/",
            {"title": "New name", "description": "New description"},
        )

        project = Project.objects.get(user=self.alice)
        self.assertRedirects(response, f"/projects/{project.id}/")
        self.assertEqual(project.title, "New name")
        self.assertEqual(project.description, "New description")
        self.assertMessages(
            response, [Message(level=25, message="Project updated successfully.")]
        )

    def test_project_settings_post_redirect(self):
        """Project settings post request redirects if not logged in."""
        response = self.client.post(
            f"/projects/{self.project.id}/settings/",
            {"title": "New name", "description": "New description"},
        )
        self.assertRedirects(
            response, f"/accounts/login/?next=/projects/{self.project.id}/settings/"
        )

    def test_project_settings_post_other_user(self):
        """Project settings post request does not work for another user."""
        self.client.login(username="bob", password="password")
        response = self.client.post(
            f"/projects/{self.project.id}/settings/",
            {"title": "New name", "description": "New description"},
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Delete project
    @mock.patch.object(Project, "remove_project_directories")
    def test_delete_project_post_request(self, remove_project_directories_mock):
        """Delete project is successful."""
        self.client.login(username="alice", password="password")
        response = self.client.post(f"/projects/{self.project.id}/delete/")

        self.assertRedirects(response, "/projects/")
        self.assertEqual(Project.objects.count(), 0)
        self.assertMessages(
            response, [Message(level=25, message="Project deleted successfully.")]
        )
        remove_project_directories_mock.assert_called_once()

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

        response = self.client.get(
            f"/projects/{project.id}/uploads/{uploaded_file.id}/"
        )
        self.assertContains(response, "<h1>test_file.mp4</h1>", html=True)

    def test_uploaded_file_detail_logged_out(self):
        """Uploaded file detail redirects if user is not logged in."""
        uploaded_file = UploadedFile.objects.first()
        project = uploaded_file.project

        response = self.client.get(
            f"/projects/{project.id}/uploads/{uploaded_file.id}/"
        )
        self.assertRedirects(
            response,
            f"/accounts/login/?next=/projects/{project.id}/uploads/{uploaded_file.id}/",
        )

    def test_uploaded_file_detail_another_user(self):
        """Uploaded file detail page of another user is not visible."""
        self.client.login(username="bob", password="password")
        uploaded_file = UploadedFile.objects.first()
        project = uploaded_file.project
        response = self.client.get(
            f"/projects/{project.id}/uploads/{uploaded_file.id}/"
        )

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

    # Create uploaded file view (JSON)
    def test_create_uploaded_file_view(self):
        """Uploaded file is created."""
        self.client.login(username="alice", password="password")
        project = Project.objects.first()
        response = self.client.post(
            f"/projects/{project.id}/create-file/",
            {"filename": "new_file.mp4", "content_type": "video/mp4", "size": "20000"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        uploaded_file = UploadedFile.objects.get(filename="new_file.mp4")
        expected = {
            "id": uploaded_file.id,
            "filename": "new_file.mp4",
        }
        self.assertJSONEqual(response.content, expected)

    def test_create_uploaded_file_errors(self):
        """Create uploaded file view error handling."""
        self.client.login(username="alice", password="password")
        project = Project.objects.first()
        response = self.client.post(
            f"/projects/{project.id}/create-file/",
            {"content_type": "video/mp4", "size": "20000"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        expected = {
            "message": "Filename is required",
        }
        self.assertJSONEqual(response.content, expected)

    @mock.patch("mmt.projects.views.get_filename_suffix", return_value="20000101103015")
    def test_create_uploaded_file_filename_exists(self, mock_suffix):
        """If filename exists within the project, a suffix is attached."""
        self.client.login(username="alice", password="password")
        response = self.client.post(
            f"/projects/{self.project.id}/create-file/",
            {"filename": "test_file.mp4", "content_type": "video/mp4", "size": "20000"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        uploaded_file = UploadedFile.objects.last()
        expected = {
            "id": uploaded_file.id,
            "filename": "test_file.mp4.20000101103015",
        }
        self.assertJSONEqual(response.content, expected)

    def test_create_uploaded_file_logged_out(self):
        """Create uploaded file returns 403 if logged out."""
        project = Project.objects.first()
        response = self.client.post(
            f"/projects/{project.id}/create-file/",
            {"filename": "new_file.mp4", "content_type": "video/mp4", "size": "20000"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_create_uploaded_file_other_user(self):
        """Create uploaded file not accessible by another user."""
        self.client.login(username="bob", password="password")
        project = Project.objects.first()
        response = self.client.post(
            f"/projects/{project.id}/create-file/",
            {"filename": "new_file.mp4", "content_type": "video/mp4", "size": "20000"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Processing requests
    # Create processing request
    def test_create_processing_request_get(self):
        """Processing request form is shown."""
        self.client.login(username="alice", password="password")
        project = Project.objects.first()
        response = self.client.get(
            f"/projects/{project.id}/processing-requests/create/"
        )

        self.assertContains(response, "<h1>New Processing Request</h1>", html=True)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.find(attrs={"data-testid": "processing-request-form"})
        self.assertIsNotNone(form)

    def test_create_processing_request_get_logged_out(self):
        """Create processing request page redirects if logged out."""
        project = Project.objects.first()
        response = self.client.get(
            f"/projects/{project.id}/processing-requests/create/"
        )

        self.assertRedirects(
            response,
            f"/accounts/login/?next=/projects/{project.id}/processing-requests/create/",
        )

    def test_create_processing_request_get_other_user(self):
        """Create processing request page is not accessible for another user."""
        self.client.login(username="bob", password="password")
        project = Project.objects.first()
        response = self.client.get(
            f"/projects/{project.id}/processing-requests/create/"
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @mock.patch("mmt.projects.tasks.send_new_processing_request_email.delay")
    def test_create_processing_request_post(self, send_email_mock):
        """Processing request is created."""
        self.client.login(username="alice", password="password")
        project = Project.objects.first()
        response = self.client.post(
            f"/projects/{project.id}/processing-requests/create/",
            {
                "description": "Transcribe my file.",
                "uploaded_files": ["test_file.mp4"],
                "make_available_on_platform": True,
            },
        )

        self.assertRedirects(response, f"/projects/{project.id}/")
        self.assertMessages(
            response,
            [Message(level=25, message="Processing request created successfully.")],
        )
        processing_request = ProcessingRequest.objects.get(
            description="Transcribe my file."
        )
        self.assertIsNotNone(processing_request)
        send_email_mock.assert_called_once()

    def test_create_processing_request_uploaded_files(self):
        """Processing request without selected uploaded files is rejected."""
        self.client.login(username="alice", password="password")
        project = Project.objects.first()
        response = self.client.post(
            f"/projects/{project.id}/processing-requests/create/",
            {"description": "Transcribe my file."},
        )
        self.assertContains(response, "At least one action must be checked.")

    def test_create_processing_request_actions(self):
        """Processing request without selecting actions is rejected."""
        self.client.login(username="alice", password="password")
        project = Project.objects.first()
        response = self.client.post(
            f"/projects/{project.id}/processing-requests/create/",
            {"description": "Transcribe my file.", "uploaded_files": ["test_file.mp4"]},
        )
        self.assertContains(response, "This field is required.")

    def test_create_processing_request_post_logged_out(self):
        """Processing request view redirects if logged out."""
        project = Project.objects.first()
        response = self.client.post(
            f"/projects/{project.id}/processing-requests/create/",
            {"description": "Transcribe my file."},
        )
        self.assertRedirects(
            response,
            f"/accounts/login/?next=/projects/{project.id}/processing-requests/create/",
        )

    def test_create_processing_request_post_other_user(self):
        """Processing request view does not work for another user."""
        self.client.login(username="bob", password="password")
        project = Project.objects.first()
        response = self.client.post(
            f"/projects/{project.id}/processing-requests/create/",
            {"description": "Transcribe my file."},
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Processing request detail
    def test_processing_request_detail(self):
        """Processing request is shown."""
        self.client.login(username="alice", password="password")
        processing_request = ProcessingRequest.objects.first()
        project = processing_request.project
        response = self.client.get(
            f"/projects/{project.id}/processing-requests/{processing_request.id}/"
        )

        self.assertContains(
            response, f"<dd class='u-ll'>Put on platform.</dd>", html=True
        )

    def test_processing_request_detail_logged_out(self):
        """Processing request page redirects if logged out."""
        processing_request = ProcessingRequest.objects.first()
        project = processing_request.project
        response = self.client.get(
            f"/projects/{project.id}/processing-requests/{processing_request.id}/"
        )

        self.assertRedirects(
            response,
            f"/accounts/login/?next=/projects/{project.id}/processing-requests/{processing_request.id}/",
        )

    def test_processing_request_detail_other_user(self):
        """Processing request page is not accessible for another user."""
        self.client.login(username="bob", password="password")
        processing_request = ProcessingRequest.objects.first()
        project = processing_request.project
        response = self.client.get(
            f"/projects/{project.id}/processing-requests/{processing_request.id}/"
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
