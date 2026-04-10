from collections import namedtuple
from http import HTTPStatus
from unittest import mock

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.base import Message
from django.contrib.messages.test import MessagesTestMixin
from django.test import TestCase

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript
from mmt.transcripts.use_cases import create_transcript
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


class UploadedFilesViewTests(TestCase, MessagesTestMixin):
    @classmethod
    def setUpTestData(cls):
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
            waveform=[108, 118, 112, 129, 118],
            waveform_sampling_rate=10,
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

        cls.uploaded_file_perms = [
            Permission.objects.get(codename='view_uploadedfile'),
            Permission.objects.get(codename='add_uploadedfile'),
            Permission.objects.get(codename='change_uploadedfile'),
            Permission.objects.get(codename='delete_uploadedfile'),
        ]
        cls.transcript_perms = [
            Permission.objects.get(codename='view_transcript'),
            Permission.objects.get(codename='add_transcript'),
            Permission.objects.get(codename='change_transcript'),
            Permission.objects.get(codename='delete_transcript'),
        ]
        cls.alice.user_permissions.add(*cls.uploaded_file_perms, *cls.transcript_perms)
        cls.bob.user_permissions.add(*cls.uploaded_file_perms)

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

    # Waveform JSON view
    def test_waveform_view(self):
        """Waveform view renders correctly."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/waveform/')
        expected = dict(
            waveform=self.uploaded_file.waveform,
            waveform_ready=True,
            waveform_sampling_rate=10,
            waveform_length=5,
            waveform_max=129,
        )
        self.assertDictEqual(response.json(), expected)

    def test_waveform_view_logged_out(self):
        """Waveform view redirects if user is not logged in."""
        response = self.client.get(
            f'/uploaded-files/{self.uploaded_file.id}/waveform/',
            headers=dict(Accept='application/json'),
        )

        self.assertRedirects(
            response,
            f'/accounts/login/?next=/uploaded-files/{self.uploaded_file.id}/waveform/',
        )

    def test_waveform_view_other_user(self):
        """Waveform view sends FORBIDDEN status if another user is logged in."""
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/waveform/')

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

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

    # Create transcript view
    def test_create_transcript_get(self):
        """Transcript form is shown."""
        self.client.login(username='alice', password='password')
        uploaded_file = self.uploaded_file
        response = self.client.get(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/'
        )

        self.assertContains(response, '<h1>Add transcript</h1>', html=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        form = soup.find(attrs={'data-testid': 'add-transcript-form'})
        self.assertIsNotNone(form)

    def test_create_transcript_get_logged_out(self):
        """Create transcript view redirects if logged out."""
        uploaded_file = self.uploaded_file
        response = self.client.get(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/'
        )

        self.assertRedirects(
            response,
            f'/accounts/login/?next=/uploaded-files/{uploaded_file.id}/create-transcript/',
        )

    def test_create_transcript_get_other_user(self):
        """Create transcript view is not accessible for another user."""
        self.bob.user_permissions.add(*self.transcript_perms)
        self.client.login(username='bob', password='password')
        uploaded_file = self.uploaded_file
        response = self.client.get(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/'
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @mock.patch('mmt.uploaded_files.views.create_transcript')
    def test_create_transcript_post(self, create_transcript_mock):
        """Transcript is created."""
        create_transcript_mock.return_value = (True, Transcript(id=5))
        self.client.login(username='alice', password='password')
        uploaded_file = self.uploaded_file
        response = self.client.post(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/',
            {
                'label': 'Test transcript',
                'language': 'en',
                'content': '{}',
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, f'/transcripts/5/')
        self.assertMessages(
            response,
            [Message(level=25, message='Transcript created successfully.')],
        )
        create_transcript_mock.assert_called_once()

    def test_create_transcript_post_logged_out(self):
        """Transcript view redirects if logged out."""
        uploaded_file = self.uploaded_file
        response = self.client.post(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/',
            {
                'label': 'Test transcript',
                'language': 'en',
                'content': '{}',
            },
        )

        self.assertRedirects(
            response,
            f'/accounts/login/?next=/uploaded-files/{uploaded_file.id}/create-transcript/',
        )

    def test_create_transcript_post_other_user(self):
        """Transcript view does not work for another user."""
        self.bob.user_permissions.add(*self.transcript_perms)
        self.client.login(username='bob', password='password')
        uploaded_file = self.uploaded_file
        response = self.client.post(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/',
            {
                'label': 'Test transcript',
                'language': 'en',
                'content': '{}',
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
