from http import HTTPStatus
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.base import Message
from django.contrib.messages.test import MessagesTestMixin
from django.test import TestCase

from mmt.projects.models import Project, ProcessingRequest
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


class UploadedFilesViewTests(TestCase, MessagesTestMixin):
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

        perm1 = Permission.objects.get(codename="view_project")
        perm2 = Permission.objects.get(codename="add_project")
        perm3 = Permission.objects.get(codename="change_project")
        perm4 = Permission.objects.get(codename="delete_project")
        perm5 = Permission.objects.get(codename="view_uploadedfile")
        perm6 = Permission.objects.get(codename="add_uploadedfile")
        perm7 = Permission.objects.get(codename="change_uploadedfile")
        perm8 = Permission.objects.get(codename="delete_uploadedfile")
        cls.alice.user_permissions.add(
            perm1, perm2, perm3, perm4, perm5, perm6, perm7, perm8
        )
        cls.bob.user_permissions.add(
            perm1, perm2, perm3, perm4, perm5, perm6, perm7, perm8
        )

    # Update uploaded file (JSON)
    def test_update_uploaded_file_request(self):
        """Update uploaded file is successful."""
        self.client.login(username="alice", password="password")

        response = self.client.post(
            f"/uploaded-files/{self.uploaded_file.id}/update/",
            {"checksum_client": "dummy-checksum"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertJSONEqual(
            response.content, {"message": "Uploaded file updated successfully."}
        )
        self.uploaded_file.refresh_from_db()
        self.assertEqual(self.uploaded_file.checksum_client, "dummy-checksum")

    def test_update_uploaded_file_error_handling(self):
        """Update uploaded file error handling."""
        self.client.login(username="alice", password="password")

        response = self.client.post(
            f"/uploaded-files/{self.uploaded_file.id}/update/",
            {},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertJSONEqual(
            response.content, {"message": "checksum_client is required."}
        )

    def test_update_uploaded_file_logged_out(self):
        """Update uploaded file returns error if logged out."""
        response = self.client.post(
            f"/uploaded-files/{self.uploaded_file.id}/update/",
            {"checksum_client": "dummy-checksum"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_update_uploaded_file_other_user(self):
        """Update uploaded file not accessible by another user."""
        self.client.login(username="bob", password="password")
        response = self.client.post(
            f"/uploaded-files/{self.uploaded_file.id}/update/",
            {"checksum_client": "dummy-checksum"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Delete uploaded file
    @mock.patch.object(UploadedFile, "delete_file")
    def test_delete_uploaded_file_request(self, delete_file_mock):
        """Delete uploaded file is successful."""
        self.client.login(username="alice", password="password")
        response = self.client.post(f"/uploaded-files/{self.uploaded_file.id}/delete/")

        self.assertRedirects(response, f"/projects/{self.project.id}/")
        self.assertEqual(UploadedFile.objects.count(), 0)
        self.assertMessages(
            response, [Message(level=25, message="Uploaded file deleted successfully.")]
        )
        delete_file_mock.assert_called_once()

    def test_delete_uploaded_file_post_redirect(self):
        """Delete uploaded file post request redirects if not logged in."""
        response = self.client.post(f"/uploaded-files/{self.uploaded_file.id}/delete/")
        self.assertRedirects(
            response,
            f"/accounts/login/?next=/uploaded-files/{self.uploaded_file.id}/delete/",
        )

    def test_delete_uploaded_file_post_other_user(self):
        """Delete uploaded file post request does not work for another user."""
        self.client.login(username="bob", password="password")
        response = self.client.post(f"/uploaded-files/{self.uploaded_file.id}/delete/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
