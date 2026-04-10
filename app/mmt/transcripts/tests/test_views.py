from http import HTTPStatus
import json
from pathlib import Path
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


class TranscriptViewTests(TestCase, MessagesTestMixin):
    @classmethod
    def setUpTestData(cls):
        with open(Path(__file__).parent / 'transcript_sample.json') as f:
            cls.transcript_data = json.load(f)

        cls.alice = User.objects.create_user(
            username='alice', password='password', email='alice@example.com'
        )
        cls.alice.accept_terms()
        cls.bob = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )
        cls.bob.accept_terms()
        _, cls.project = create_project(title='Test project', user=cls.alice)
        cls.uploaded_file = UploadedFile.objects.create(
            project=cls.project,
            filename='test_file.mp4',
            has_file=True,
            size=20000,
            transferred=20000,
            media_type='video/mp4',
        )
        _, cls.transcript = create_transcript(
            label='Test transcript',
            language='en',
            content=cls.transcript_data,
            uploaded_file=cls.uploaded_file,
        )

        uploaded_file_perms = [
            Permission.objects.get(codename='view_uploadedfile'),
            Permission.objects.get(codename='add_uploadedfile'),
            Permission.objects.get(codename='change_uploadedfile'),
            Permission.objects.get(codename='delete_uploadedfile'),
        ]
        transcript_perms = [
            Permission.objects.get(codename='view_transcript'),
            Permission.objects.get(codename='add_transcript'),
            Permission.objects.get(codename='change_transcript'),
            Permission.objects.get(codename='delete_transcript'),
        ]
        cls.alice.user_permissions.add(*uploaded_file_perms, *transcript_perms)
        cls.bob.user_permissions.add(*uploaded_file_perms, *transcript_perms)

    # Detail view
    def test_detail_view(self):
        """Detail view renders correctly."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/transcripts/{self.transcript.id}/')
        self.assertContains(response, '<h1>Test transcript</h1>', html=True)

    def test_detail_view_logged_out(self):
        """Detail view redirects if user is not logged in."""
        response = self.client.get(f'/transcripts/{self.transcript.id}/')
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/transcripts/{self.transcript.id}/',
        )

    def test_detail_view_other_user(self):
        """Detail view of another user is not visible."""
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/transcripts/{self.transcript.id}/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Edit view
    def test_edit_view(self):
        """Edit view renders correctly."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/transcripts/{self.transcript.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_view_logged_out(self):
        """Edit view redirects if user is not logged in."""
        response = self.client.get(f'/transcripts/{self.transcript.id}/edit/')
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/transcripts/{self.transcript.id}/edit/',
        )

    def test_edit_view_other_user(self):
        """Edit view of another user is not visible."""
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/transcripts/{self.transcript.id}/edit/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # JSON view
    def test_json_view(self):
        """JSON view renders correctly."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/transcripts/{self.transcript.id}/json/')
        self.assertDictEqual(response.json(), self.transcript_data)

    def test_json_view_logged_out(self):
        """JSON view redirects if user is not logged in."""
        response = self.client.get(
            f'/transcripts/{self.transcript.id}/json/',
            headers=dict(Accept='application/json'),
        )

        self.assertRedirects(
            response,
            f'/accounts/login/?next=/transcripts/{self.transcript.id}/json/',
        )

    def test_json_view_other_user(self):
        """JSON view sends FORBIDDEN status if another user is logged in."""
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/transcripts/{self.transcript.id}/json/')

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    # Update transcript (JSON)
    def test_update_transcript_request(self):
        """Update transcript is successful."""
        self.client.login(username='alice', password='password')

        response = self.client.post(
            f'/transcripts/{self.transcript.id}/update/',
            {'content': {'segments': []}},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertJSONEqual(
            response.content, {'message': 'Transcript updated successfully.'}
        )
        self.transcript.refresh_from_db()
        self.assertEqual(self.transcript.content['segments'], [])

    def test_update_transcript_error_handling(self):
        """Update transcript error handling."""
        self.client.login(username='alice', password='password')

        response = self.client.post(
            f'/transcripts/{self.transcript.id}/update/',
            {},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertJSONEqual(response.content, {'message': 'content is required.'})

    def test_update_transcript_logged_out(self):
        """Update transcript returns error if logged out."""
        response = self.client.post(
            f'/transcripts/{self.transcript.id}/update/',
            {'content': '{"segments": []}'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_update_transcript_other_user(self):
        """Update transcript not accessible by another user."""
        self.client.login(username='bob', password='password')
        response = self.client.post(
            f'/transcripts/{self.transcript.id}/update/',
            {'content': '{"segments": []}'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Delete view
    @mock.patch('mmt.transcripts.views.delete_transcript')
    def test_delete_view(self, delete_transcript_mock):
        """Delete view works properly."""
        delete_transcript_mock.return_value = True
        self.client.login(username='alice', password='password')

        response = self.client.post(f'/transcripts/{self.transcript.id}/delete/')

        self.assertRedirects(response, f'/uploaded-files/{self.uploaded_file.id}/')
        self.assertMessages(
            response, [Message(level=25, message='Transcript deleted successfully.')]
        )
        delete_transcript_mock.assert_called_once()

    @mock.patch('mmt.transcripts.views.delete_transcript')
    def test_delete_view_failure(self, delete_transcript_mock):
        """Delete view fails."""
        delete_transcript_mock.return_value = False
        self.client.login(username='alice', password='password')

        response = self.client.post(f'/transcripts/{self.transcript.id}/delete/')

        self.assertEqual(response.status_code, 500)
        delete_transcript_mock.assert_called_once()

    def test_delete_view_logged_out(self):
        """Delete transcript view redirects if not logged in."""
        response = self.client.post(f'/transcripts/{self.transcript.id}/delete/')
        self.assertRedirects(
            response, f'/accounts/login/?next=/transcripts/{self.transcript.id}/delete/'
        )

    def test_delete_view_other_user(self):
        """Delete transcript view does not work for another user."""
        self.client.login(username='bob', password='password')
        response = self.client.post(f'/transcripts/{self.transcript.id}/delete/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
