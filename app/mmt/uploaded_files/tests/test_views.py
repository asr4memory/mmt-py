from http import HTTPStatus
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.base import Message
from django.contrib.messages.test import MessagesTestMixin
from django.test import TestCase

from mmt.projects.use_cases import create_project
from mmt.transcripts.use_cases import create_transcript
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


class UploadedFilesViewTests(TestCase, MessagesTestMixin):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='alice', password='password', email='alice@example.com'
        )
        cls.bob = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )
        _, cls.project = create_project(title='Test project', user=cls.alice)
        cls.uploaded_file = UploadedFile.objects.create(
            project=cls.project,
            filename='test_file.mp4',
            has_file=True,
            size=20000,
            transferred=20000,
            media_type='video/mp4',
        )

        _, cls.project_bob = create_project(title='Bobs project', user=cls.bob)
        cls.uploaded_file_bob = UploadedFile.objects.create(
            project=cls.project_bob,
            filename='bobs_file.mp4',
            has_file=True,
            size=10000,
            transferred=10000,
            media_type='audio/mp3',
        )

        perm1 = Permission.objects.get(codename='view_uploadedfile')
        perm2 = Permission.objects.get(codename='add_uploadedfile')
        perm3 = Permission.objects.get(codename='change_uploadedfile')
        perm4 = Permission.objects.get(codename='delete_uploadedfile')
        perm5 = Permission.objects.get(codename='view_transcript')
        perm6 = Permission.objects.get(codename='add_transcript')
        perm7 = Permission.objects.get(codename='change_transcript')
        perm8 = Permission.objects.get(codename='delete_transcript')
        cls.alice.user_permissions.add(
            perm1, perm2, perm3, perm4, perm5, perm6, perm7, perm8
        )
        cls.bob.user_permissions.add(perm1, perm2, perm3, perm4)

    # Uploaded file detail
    def test_detail_view(self):
        """Detail page renders correctly."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/')
        self.assertContains(response, '<h1>test_file.mp4</h1>', html=True)
        self.assertContains(response, '<h2>Transcripts</h2>', html=True)
        self.assertContains(response, 'There are no transcripts yet.')

    def test_detail_view_transcript_table(self):
        """Detail page shows transcript table."""
        _, transcript = create_transcript(
            label='Test transcript', uploaded_file=self.uploaded_file
        )
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/')
        self.assertContains(response, '<h2>Transcripts</h2>', html=True)
        self.assertContains(
            response,
            f'<a href="/transcripts/{transcript.id}/">Test transcript</a>',
            html=True,
        )

    def test_detail_view_wo_transcript_perms(self):
        """Detail does not show transcript section."""
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file_bob.id}/')
        self.assertContains(response, '<h1>bobs_file.mp4</h1>', html=True)
        self.assertNotContains(response, '<h2>Transcripts</h2>')

    def test_uploaded_file_detail_logged_out(self):
        """Detail view redirects if user is not logged in."""
        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/')
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/uploaded-files/{self.uploaded_file.id}/',
        )

    def test_uploaded_file_detail_another_user(self):
        """Detail view of another user is not visible."""
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Update uploaded file (JSON)
    def test_update_uploaded_file_request(self):
        """Update uploaded file is successful."""
        self.client.login(username='alice', password='password')

        response = self.client.post(
            f'/uploaded-files/{self.uploaded_file.id}/update/',
            {'checksum_client': 'dummy-checksum'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertJSONEqual(
            response.content, {'message': 'Uploaded file updated successfully.'}
        )
        self.uploaded_file.refresh_from_db()
        self.assertEqual(self.uploaded_file.checksum_client, 'dummy-checksum')

    def test_update_uploaded_file_error_handling(self):
        """Update uploaded file error handling."""
        self.client.login(username='alice', password='password')

        response = self.client.post(
            f'/uploaded-files/{self.uploaded_file.id}/update/',
            {},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertJSONEqual(
            response.content, {'message': 'checksum_client is required.'}
        )

    def test_update_uploaded_file_logged_out(self):
        """Update uploaded file returns error if logged out."""
        response = self.client.post(
            f'/uploaded-files/{self.uploaded_file.id}/update/',
            {'checksum_client': 'dummy-checksum'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_update_uploaded_file_other_user(self):
        """Update uploaded file not accessible by another user."""
        self.client.login(username='bob', password='password')
        response = self.client.post(
            f'/uploaded-files/{self.uploaded_file.id}/update/',
            {'checksum_client': 'dummy-checksum'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Delete uploaded file
    @mock.patch.object(UploadedFile, 'delete_file')
    def test_delete_uploaded_file_request(self, delete_file_mock):
        """Delete uploaded file is successful."""
        self.client.login(username='alice', password='password')
        response = self.client.post(f'/uploaded-files/{self.uploaded_file.id}/delete/')

        self.assertRedirects(response, f'/projects/{self.project.id}/')
        self.assertEqual(
            UploadedFile.objects.filter(project__user_id=self.alice.id).count(), 0
        )
        self.assertMessages(
            response, [Message(level=25, message='Uploaded file deleted successfully.')]
        )
        delete_file_mock.assert_called_once()

    def test_delete_uploaded_file_post_redirect(self):
        """Delete uploaded file post request redirects if not logged in."""
        response = self.client.post(f'/uploaded-files/{self.uploaded_file.id}/delete/')
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/uploaded-files/{self.uploaded_file.id}/delete/',
        )

    def test_delete_uploaded_file_post_other_user(self):
        """Delete uploaded file post request does not work for another user."""
        self.client.login(username='bob', password='password')
        response = self.client.post(f'/uploaded-files/{self.uploaded_file.id}/delete/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
