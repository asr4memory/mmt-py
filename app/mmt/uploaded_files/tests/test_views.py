from collections import namedtuple
from http import HTTPStatus
from unittest import mock

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.base import Message
from django.contrib.messages.test import MessagesTestMixin
from django.test import TestCase

from django.core.files.uploadedfile import SimpleUploadedFile

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript
from mmt.uploaded_files.models import CHUNK_SIZE, FileChunk, UploadedFile, Waveform
from mmt.uploaded_files.analysis import SAMPLING_RATE

User = get_user_model()


class UploadedFilesViewTests(TestCase, MessagesTestMixin):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='alice',
            password='password',
            email='alice@example.com',
            terms_accepted_version=1,
        )
        cls.bob = User.objects.create_user(
            username='bob',
            password='password',
            email='bob@example.com',
            terms_accepted_version=1,
        )
        _, cls.project = create_project(title='Test project', user=cls.alice)
        cls.uploaded_file = UploadedFile.objects.create(
            project=cls.project,
            filename='test_file.mp4',
            has_file=True,
            size=20000,
            media_type='video/mp4',
        )
        cls.waveform = Waveform.objects.create(
            uploaded_file=cls.uploaded_file,
            data=[108, 118, 112, 129, 118],
        )

        _, cls.project_bob = create_project(title='Bobs project', user=cls.bob)
        cls.uploaded_file_bob = UploadedFile.objects.create(
            project=cls.project_bob,
            filename='bobs_file.mp4',
            has_file=True,
            size=10000,
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
        transcript = Transcript.objects.create(
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

    # Detail view context
    def test_detail_show_transferred_true_when_incomplete(self):
        """show_transferred is True when the file has chunks but is not yet assembled."""
        incomplete_file = UploadedFile.objects.create(
            project=self.project,
            filename='incomplete.mp4',
            media_type='video/mp4',
            size=2 * CHUNK_SIZE,
        )
        FileChunk.objects.create(uploaded_file=incomplete_file, index=0)
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{incomplete_file.id}/')

        self.assertTrue(response.context['show_transferred'])

    def test_detail_show_transferred_false_when_not_incomplete(self):
        """show_transferred is False when the file has no chunks (missing status)."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/')

        self.assertFalse(response.context['show_transferred'])

    # Waveform JSON view
    def test_waveform_view(self):
        """Waveform view renders correctly."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/waveform/')
        expected = dict(
            waveform=self.waveform.data,
            waveform_sampling_rate=SAMPLING_RATE,
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

    def test_waveform_view_no_waveform(self):
        """Waveform view returns JSON 404 if no waveform exists for the file."""
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file_bob.id}/waveform/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertJSONEqual(response.content, {'message': 'Waveform not found.'})

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

    def test_create_transcript_post(self):
        """Transcript is created."""
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

        transcript = Transcript.objects.get(uploaded_file=uploaded_file, label='Test transcript')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, f'/transcripts/{transcript.id}/')
        self.assertMessages(
            response,
            [Message(level=25, message='Transcript created successfully.')],
        )

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

    # Upload chunk view
    @mock.patch('mmt.uploaded_files.views.upload_chunk', return_value=False)
    def test_upload_chunk(self, mock_upload_chunk):
        """Chunk is accepted; upload not yet complete."""
        self.client.login(username='alice', password='password')

        response = self.client.post(
            f'/uploaded-files/{self.uploaded_file.id}/upload/0/',
            data={'file': SimpleUploadedFile('chunk', b'chunk data')},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertJSONEqual(response.content, {'complete': False})
        mock_upload_chunk.assert_called_once_with(
            self.uploaded_file, index=0, data=b'chunk data'
        )

    @mock.patch('mmt.uploaded_files.views.upload_chunk', return_value=True)
    def test_upload_chunk_complete(self, mock_upload_chunk):
        """Chunk is accepted and upload is now complete."""
        self.client.login(username='alice', password='password')

        response = self.client.post(
            f'/uploaded-files/{self.uploaded_file.id}/upload/0/',
            data={'file': SimpleUploadedFile('chunk', b'chunk data')},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertJSONEqual(response.content, {'complete': True})

    @mock.patch(
        'mmt.uploaded_files.views.upload_chunk',
        side_effect=ValueError('Invalid chunk index 99 for file with 2 chunks.'),
    )
    def test_upload_chunk_invalid_index(self, mock_upload_chunk):
        """Invalid chunk index returns 400."""
        self.client.login(username='alice', password='password')

        response = self.client.post(
            f'/uploaded-files/{self.uploaded_file.id}/upload/99/',
            data={'file': SimpleUploadedFile('chunk', b'chunk data')},
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertJSONEqual(
            response.content,
            {'message': 'Invalid chunk index 99 for file with 2 chunks.'},
        )

    @mock.patch(
        'mmt.uploaded_files.views.upload_chunk', side_effect=OSError('Disk full')
    )
    def test_upload_chunk_server_error(self, mock_upload_chunk):
        """Unexpected errors return 500 with a JSON body."""
        self.client.login(username='alice', password='password')

        response = self.client.post(
            f'/uploaded-files/{self.uploaded_file.id}/upload/0/',
            data={'file': SimpleUploadedFile('chunk', b'chunk data')},
        )

        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertJSONEqual(response.content, {'message': 'Disk full'})

    def test_upload_chunk_no_file(self):
        """Missing file field returns 400."""
        self.client.login(username='alice', password='password')

        response = self.client.post(
            f'/uploaded-files/{self.uploaded_file.id}/upload/0/',
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertJSONEqual(response.content, {'message': 'No file provided.'})

    def test_upload_chunk_logged_out(self):
        """Chunk upload returns 403 if not logged in."""
        response = self.client.post(
            f'/uploaded-files/{self.uploaded_file.id}/upload/0/',
            data={'file': SimpleUploadedFile('chunk', b'chunk data')},
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_upload_chunk_other_user(self):
        """Chunk upload is not accessible by another user."""
        self.client.login(username='bob', password='password')

        response = self.client.post(
            f'/uploaded-files/{self.uploaded_file.id}/upload/0/',
            data={'file': SimpleUploadedFile('chunk', b'chunk data')},
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Status JSON view
    def test_status_view_complete(self):
        """Returns 'complete' and empty chunk lists when the file is fully assembled."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/status/')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertJSONEqual(
            response.content,
            {
                'id': self.uploaded_file.id,
                'filename': 'test_file.mp4',
                'original_filename': '',
                'size': 20000,
                'media_type': 'video/mp4',
                'chunks_total': 1,
                'chunks_received': [],
                'chunks_missing': [],
                'transferred': 0,
                'status': 'complete',
            },
        )

    def test_status_view_logged_out(self):
        """Status view returns 403 if not logged in."""
        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/status/')

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_status_view_other_user(self):
        """Status view is not accessible by another user."""
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/status/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

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

    @mock.patch('mmt.uploaded_files.views.task_extract_waveform_data')
    def test_create_transcript_post_triggers_waveform_task(self, task_mock):
        """Waveform task is triggered when transcript is created and no waveform exists."""
        uploaded_file = UploadedFile.objects.create(
            project=self.project,
            filename='no_waveform_file.mp4',
            has_file=True,
            size=15000,
            media_type='video/mp4',
        )
        self.client.login(username='alice', password='password')
        self.client.post(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/',
            {'label': 'Test transcript', 'language': 'en', 'content': '{}'},
        )

        task_mock.delay.assert_called_once_with(uploaded_file.id)
