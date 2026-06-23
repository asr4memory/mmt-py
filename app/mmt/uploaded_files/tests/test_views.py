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

from mmt.my_account.models import FeatureFlag
from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript
from django.conf import settings

from mmt.uploaded_files.models import FileChunk, UploadedFile, Waveform
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
        FeatureFlag.objects.create(user=cls.alice, name=FeatureFlag.Name.CHUNKED_UPLOAD)
        cls.bob = User.objects.create_user(
            username='bob',
            password='password',
            email='bob@example.com',
            terms_accepted_version=1,
        )
        cls.project = create_project(title='Test project', user=cls.alice)
        cls.uploaded_file = UploadedFile.objects.create(
            project=cls.project,
            filename='test_file.mp4',
            original_filename='test_file.mp4',
            has_file=True,
            size=20000,
            media_type='video/mp4',
        )
        cls.waveform = Waveform.objects.create(
            uploaded_file=cls.uploaded_file,
            data=[108, 118, 112, 129, 118],
        )

        cls.project_bob = create_project(title='Bobs project', user=cls.bob)
        cls.uploaded_file_bob = UploadedFile.objects.create(
            project=cls.project_bob,
            filename='bobs_file.mp4',
            original_filename='bobs_file.mp4',
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

    def test_detail_view_shows_corruption_warning(self):
        """Detail page warns when client and server checksums disagree."""
        self.uploaded_file.checksum_client = 'aaa'
        self.uploaded_file.checksum_server = 'bbb'
        self.uploaded_file.save()
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/')
        self.assertContains(response, 'data-testid="corruption-warning"')

    def test_detail_view_polls_while_processing(self):
        """A processing file's detail page polls the status endpoint to auto-refresh."""
        processing_file = UploadedFile.objects.create(
            project=self.project,
            filename='processing.mp4',
            original_filename='processing.mp4',
            assembling=True,
            size=20000,
            media_type='video/mp4',
        )
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{processing_file.id}/')

        self.assertContains(response, 'pill--processing')
        self.assertContains(response, 'x-init="poll()"')

    def test_detail_view_does_not_poll_when_complete(self):
        """A fully assembled file's detail page has no polling attached."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/')

        self.assertNotContains(response, 'x-init="poll()"')

    def test_detail_view_no_corruption_warning_when_checksums_match(self):
        """Detail page does not warn when checksums match."""
        self.uploaded_file.checksum_client = 'aaa'
        self.uploaded_file.checksum_server = 'aaa'
        self.uploaded_file.save()
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/')
        self.assertNotContains(response, 'data-testid="corruption-warning"')

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
    def test_detail_chunked_upload_enabled_when_flag_set(self):
        """chunked_upload_enabled is True when the user has the chunked_upload flag."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/')

        self.assertTrue(response.context['chunked_upload_enabled'])

    def test_detail_chunked_upload_disabled_without_flag(self):
        """chunked_upload_enabled is False when the user lacks the chunked_upload flag."""
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file_bob.id}/')

        self.assertFalse(response.context['chunked_upload_enabled'])

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

        response = self.client.get(
            f'/uploaded-files/{self.uploaded_file_bob.id}/waveform/'
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertJSONEqual(response.content, {'message': 'Waveform not found.'})

    # Stream uploaded file (inline media playback with range support)
    def _write_stream_file(self, content=b'0123456789'):
        file_path = self.uploaded_file.file_path
        file_path.write_bytes(content)
        self.addCleanup(file_path.unlink, missing_ok=True)
        return file_path

    def test_stream_full_content(self):
        """Without a Range header the whole file is returned with metadata."""
        self._write_stream_file(b'0123456789')
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/stream/')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response['Content-Type'], 'video/mp4')
        self.assertEqual(response['Accept-Ranges'], 'bytes')
        self.assertEqual(response['Content-Length'], '10')
        self.assertEqual(response['Content-Disposition'], 'inline')
        self.assertEqual(b''.join(response.streaming_content), b'0123456789')

    def test_stream_range_request(self):
        """A bounded Range header yields a 206 with the requested slice."""
        self._write_stream_file(b'0123456789')
        self.client.login(username='alice', password='password')

        response = self.client.get(
            f'/uploaded-files/{self.uploaded_file.id}/stream/',
            headers={'range': 'bytes=2-5'},
        )

        self.assertEqual(response.status_code, HTTPStatus.PARTIAL_CONTENT)
        self.assertEqual(response['Content-Range'], 'bytes 2-5/10')
        self.assertEqual(response['Content-Length'], '4')
        self.assertEqual(b''.join(response.streaming_content), b'2345')

    def test_stream_open_ended_range(self):
        """An open-ended Range header streams to the end of the file."""
        self._write_stream_file(b'0123456789')
        self.client.login(username='alice', password='password')

        response = self.client.get(
            f'/uploaded-files/{self.uploaded_file.id}/stream/',
            headers={'range': 'bytes=4-'},
        )

        self.assertEqual(response.status_code, HTTPStatus.PARTIAL_CONTENT)
        self.assertEqual(response['Content-Range'], 'bytes 4-9/10')
        self.assertEqual(response['Content-Length'], '6')
        self.assertEqual(b''.join(response.streaming_content), b'456789')

    def test_stream_suffix_range(self):
        """A suffix Range header streams the last N bytes."""
        self._write_stream_file(b'0123456789')
        self.client.login(username='alice', password='password')

        response = self.client.get(
            f'/uploaded-files/{self.uploaded_file.id}/stream/',
            headers={'range': 'bytes=-3'},
        )

        self.assertEqual(response.status_code, HTTPStatus.PARTIAL_CONTENT)
        self.assertEqual(response['Content-Range'], 'bytes 7-9/10')
        self.assertEqual(response['Content-Length'], '3')
        self.assertEqual(b''.join(response.streaming_content), b'789')

    def test_stream_unsatisfiable_range(self):
        """A Range starting beyond the file size yields a 416."""
        self._write_stream_file(b'0123456789')
        self.client.login(username='alice', password='password')

        response = self.client.get(
            f'/uploaded-files/{self.uploaded_file.id}/stream/',
            headers={'range': 'bytes=20-30'},
        )

        self.assertEqual(
            response.status_code, HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE
        )
        self.assertEqual(response['Content-Range'], 'bytes */10')

    def test_stream_file_missing(self):
        """Streaming a file that is not on disk returns a 404."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/stream/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_stream_logged_out(self):
        """Streaming redirects to the login page when logged out."""
        self._write_stream_file()

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/stream/')

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_stream_other_user(self):
        """A user cannot stream another user's file."""
        self._write_stream_file()
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/stream/')

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

    def test_update_uploaded_file_logs_on_checksum_mismatch(self):
        """Submitting a client checksum that differs from the server one warns."""
        self.client.login(username='alice', password='password')
        self.uploaded_file.checksum_server = 'server-sum'
        self.uploaded_file.save()

        with self.assertLogs('mmt.uploaded_files.models', level='WARNING') as cm:
            self.client.post(
                f'/uploaded-files/{self.uploaded_file.id}/update/',
                {'checksum_client': 'client-sum'},
                content_type='application/json',
            )

        self.assertTrue(any('Checksum mismatch' in line for line in cm.output))

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

        transcript = Transcript.objects.get(
            uploaded_file=uploaded_file, label='Test transcript'
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, f'/transcripts/{transcript.id}/')
        self.assertMessages(
            response,
            [Message(level=25, message='Transcript created successfully.')],
        )

    def test_create_transcript_post_from_file(self):
        """Transcript is created from an uploaded JSON file."""
        self.client.login(username='alice', password='password')
        uploaded_file = self.uploaded_file
        json_file = SimpleUploadedFile(
            'transcript.json', b'{"segments": []}', content_type='application/json'
        )
        response = self.client.post(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/',
            {
                'label': 'From file',
                'language': 'en',
                'content_source': 'file',
                'content_file': json_file,
            },
        )

        transcript = Transcript.objects.get(
            uploaded_file=uploaded_file, label='From file'
        )
        self.assertEqual(transcript.content, {'segments': []})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, f'/transcripts/{transcript.id}/')

    def test_create_transcript_post_from_invalid_file(self):
        """Invalid JSON file re-renders the form with an error."""
        self.client.login(username='alice', password='password')
        uploaded_file = self.uploaded_file
        bad_file = SimpleUploadedFile(
            'transcript.json', b'not json', content_type='application/json'
        )
        response = self.client.post(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/',
            {
                'label': 'From file',
                'language': 'en',
                'content_source': 'file',
                'content_file': bad_file,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(
            Transcript.objects.filter(
                uploaded_file=uploaded_file, label='From file'
            ).exists()
        )
        self.assertContains(response, 'The uploaded file is not valid JSON.')

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
                'original_filename': 'test_file.mp4',
                'size': 20000,
                'media_type': 'video/mp4',
                'chunks_total': 1,
                'chunks_received': [],
                'chunks_missing': [],
                'transferred': 0,
                'status': 'complete',
            },
        )

    def test_status_view_processing(self):
        """Returns 'processing' while assembly has been queued but not finished."""
        processing_file = UploadedFile.objects.create(
            project=self.project,
            filename='processing.mp4',
            original_filename='processing.mp4',
            assembling=True,
            size=20000,
            media_type='video/mp4',
        )
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{processing_file.id}/status/')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()['status'], 'processing')

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

    # Resume upload view
    def test_resume_upload_renders_for_incomplete_file(self):
        """Resume upload page is shown for a file with chunks but not yet assembled."""
        incomplete_file = UploadedFile.objects.create(
            project=self.project,
            filename='partial.mp4',
            original_filename='partial.mp4',
            media_type='video/mp4',
            size=2 * settings.MMT_UPLOAD_CHUNK_SIZE,
        )
        FileChunk.objects.create(uploaded_file=incomplete_file, index=0)
        self.client.login(username='alice', password='password')

        response = self.client.get(
            f'/uploaded-files/{incomplete_file.id}/resume-upload/'
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, 'uploaded_files/resume_upload.html')

    def test_resume_upload_context(self):
        """Context contains the expected variables for the frontend."""
        incomplete_file = UploadedFile.objects.create(
            project=self.project,
            filename='partial_ctx.mp4',
            original_filename='partial_ctx.mp4',
            media_type='video/mp4',
            size=2 * settings.MMT_UPLOAD_CHUNK_SIZE,
        )
        FileChunk.objects.create(uploaded_file=incomplete_file, index=0)
        self.client.login(username='alice', password='password')

        response = self.client.get(
            f'/uploaded-files/{incomplete_file.id}/resume-upload/'
        )

        self.assertEqual(response.context['uploaded_file'], incomplete_file)
        self.assertEqual(response.context['project'], self.project)
        # chunk 0 received, chunk 1 missing
        self.assertEqual(response.context['chunks_missing'], [1])
        self.assertEqual(response.context['chunks_total'], 2)
        self.assertEqual(response.context['chunk_size'], settings.MMT_UPLOAD_CHUNK_SIZE)
        self.assertNotIn('chunked_upload', response.context)

    def test_resume_upload_redirects_if_complete(self):
        """Redirects to the detail view when the file is already fully uploaded."""
        self.client.login(username='alice', password='password')

        response = self.client.get(
            f'/uploaded-files/{self.uploaded_file.id}/resume-upload/'
        )

        self.assertRedirects(response, f'/uploaded-files/{self.uploaded_file.id}/')

    def test_resume_upload_redirects_if_missing(self):
        """Redirects to the detail view when no chunks have been uploaded yet."""
        missing_file = UploadedFile.objects.create(
            project=self.project,
            filename='not_started.mp4',
            original_filename='not_started.mp4',
            media_type='video/mp4',
            size=settings.MMT_UPLOAD_CHUNK_SIZE,
        )
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{missing_file.id}/resume-upload/')

        self.assertRedirects(response, f'/uploaded-files/{missing_file.id}/')

    def test_resume_upload_forbidden_without_flag(self):
        """Returns 403 when the chunked_upload feature flag is not enabled for the user."""
        user_no_flag = User.objects.create_user(
            username='carol',
            password='password',
            email='carol@example.com',
            terms_accepted_version=1,
        )
        project_carol = create_project(title='Carol project', user=user_no_flag)
        user_no_flag.user_permissions.add(*self.uploaded_file_perms)
        incomplete_file = UploadedFile.objects.create(
            project=project_carol,
            filename='partial_flag.mp4',
            original_filename='partial_flag.mp4',
            media_type='video/mp4',
            size=settings.MMT_UPLOAD_CHUNK_SIZE,
        )
        FileChunk.objects.create(uploaded_file=incomplete_file, index=0)
        self.client.login(username='carol', password='password')

        response = self.client.get(
            f'/uploaded-files/{incomplete_file.id}/resume-upload/'
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_resume_upload_logged_out(self):
        """Resume upload redirects to login when not authenticated."""
        incomplete_file = UploadedFile.objects.create(
            project=self.project,
            filename='partial_auth.mp4',
            original_filename='partial_auth.mp4',
            media_type='video/mp4',
            size=settings.MMT_UPLOAD_CHUNK_SIZE,
        )
        FileChunk.objects.create(uploaded_file=incomplete_file, index=0)

        response = self.client.get(
            f'/uploaded-files/{incomplete_file.id}/resume-upload/'
        )

        self.assertRedirects(
            response,
            f'/accounts/login/?next=/uploaded-files/{incomplete_file.id}/resume-upload/',
        )

    def test_resume_upload_other_user(self):
        """Resume upload returns 404 when accessed by a different user."""
        incomplete_file = UploadedFile.objects.create(
            project=self.project,
            filename='partial_other.mp4',
            original_filename='partial_other.mp4',
            media_type='video/mp4',
            size=settings.MMT_UPLOAD_CHUNK_SIZE,
        )
        FileChunk.objects.create(uploaded_file=incomplete_file, index=0)
        self.client.login(username='bob', password='password')

        response = self.client.get(
            f'/uploaded-files/{incomplete_file.id}/resume-upload/'
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
