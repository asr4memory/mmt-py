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
            transcript_data = json.load(f)

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
        _, cls.transcript = create_transcript(
            label='Test transcript',
            language='en',
            content=transcript_data,
            uploaded_file=cls.uploaded_file,
        )

        perm1 = Permission.objects.get(codename='view_transcript')
        perm2 = Permission.objects.get(codename='add_transcript')
        perm3 = Permission.objects.get(codename='change_transcript')
        perm4 = Permission.objects.get(codename='delete_transcript')
        cls.alice.user_permissions.add(perm1, perm2, perm3, perm4)
        cls.bob.user_permissions.add(perm1, perm2, perm3, perm4)

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
        self.assertContains(response, '<h1>Test transcript</h1>', html=True)

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
        self.assertDictEqual(response.json(), self.transcript.content)

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
