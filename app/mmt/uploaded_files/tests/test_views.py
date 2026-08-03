import json
from http import HTTPStatus
from unittest import mock

import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.base import Message
from django.contrib.messages.test import MessagesTestMixin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from mmt.my_account.models import FeatureFlag
from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript
from mmt.uploaded_files.media import SAMPLING_RATE
from mmt.uploaded_files.models import FileChunk, UploadedFile, Waveform

User = get_user_model()

TRANSCRIPT_CONTENT = {
    'language': 'en',
    'segments': [
        {
            'start': 0.0,
            'end': 1.0,
            'text': 'Hello world',
            'words': [
                {'word': 'Hello', 'start': 0.0, 'end': 0.5},
                {'word': 'world', 'start': 0.5, 'end': 1.0},
            ],
        }
    ],
}


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

    def test_detail_view_video_source_omits_type(self):
        """The media source has no type attribute so the browser sniffs the content.

        A type attribute on a single source only lets browsers pre-emptively
        reject it (e.g. Firefox refusing video/ogg) without ever fetching it.
        """
        self.client.login(username='alice', password='password')

        with mock.patch.object(UploadedFile, 'update_has_file_field'):
            response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/')

        soup = BeautifulSoup(response.content, 'html.parser')
        source = soup.select_one('video source')
        self.assertIsNotNone(source)
        self.assertNotIn('type', source.attrs)

    def test_detail_view_renders_unsupported_video_fallback(self):
        """A video carries a hidden fallback the client reveals if it can't decode it."""
        self.client.login(username='alice', password='password')

        with mock.patch.object(UploadedFile, 'update_has_file_field'):
            response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/')

        soup = BeautifulSoup(response.content, 'html.parser')
        fallback = soup.select_one('[data-testid="video-unsupported"]')
        self.assertIsNotNone(fallback)
        self.assertTrue(fallback.has_attr('hidden'))

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
        self.assertContains(
            response,
            f"uploadStatusPoller('/uploaded-files/{processing_file.id}/status/')",
        )

    def test_detail_view_does_not_poll_when_complete(self):
        """A fully assembled file's detail page has no polling attached."""
        self.client.login(username='alice', password='password')

        with mock.patch.object(UploadedFile, 'update_has_file_field'):
            response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/')

        self.assertContains(response, 'pill--complete')
        self.assertNotContains(response, 'uploadStatusPoller')

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

    # Download uploaded file (forced download). Range behaviour is shared with
    # the stream view via serve_file and covered by the stream tests above.
    def test_download_forces_attachment(self):
        """The download view serves the file as a named attachment."""
        self._write_stream_file(b'0123456789')
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/download/')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response['Content-Type'], 'application/octet-stream')
        self.assertEqual(
            response['Content-Disposition'], 'attachment; filename="test_file.mp4"'
        )
        self.assertEqual(b''.join(response.streaming_content), b'0123456789')

    def test_download_logged_out(self):
        """Downloading redirects to the login page when logged out."""
        self._write_stream_file()

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/download/')

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_download_other_user(self):
        """A user cannot download another user's file."""
        self._write_stream_file()
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/uploaded-files/{self.uploaded_file.id}/download/')

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

    @mock.patch('mmt.uploaded_files.views.ensure_transcript_editing_media')
    def test_create_transcript_post(self, mock_ensure):
        """Transcript is created.

        The editing media is patched because creating a transcript enqueues
        the transcode of the web video, which would need a running broker.
        """
        self.client.login(username='alice', password='password')
        uploaded_file = self.uploaded_file
        response = self.client.post(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/',
            {
                'label': 'Test transcript',
                'content': json.dumps(TRANSCRIPT_CONTENT),
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

    @mock.patch('mmt.uploaded_files.views.ensure_transcript_editing_media')
    def test_create_transcript_normalizes_pasted_content(self, mock_ensure):
        """Pasted Whisper JSON is stored in the normalized mmt-transcript format."""
        self.client.login(username='alice', password='password')
        uploaded_file = self.uploaded_file
        self.client.post(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/',
            {
                'label': 'Normalized',
                'content': json.dumps(TRANSCRIPT_CONTENT),
            },
        )

        transcript = Transcript.objects.get(
            uploaded_file=uploaded_file, label='Normalized'
        )
        content = transcript.content
        self.assertEqual(content['format'], 'mmt-transcript')
        self.assertEqual(content['version'], 1)
        # The language is taken from the pasted JSON, not from a form field.
        self.assertEqual(content['language'], 'en')
        self.assertEqual(content['speakers'], [])
        word = content['segments'][0]['words'][0]
        self.assertTrue(word['id'].startswith('wrd_'))
        self.assertIsNone(word['speakerId'])

    @mock.patch('mmt.uploaded_files.views.ensure_transcript_editing_media')
    def test_create_transcript_post_from_file(self, mock_ensure):
        """Transcript is created from an uploaded JSON file."""
        self.client.login(username='alice', password='password')
        uploaded_file = self.uploaded_file
        json_file = SimpleUploadedFile(
            'transcript.json',
            json.dumps(TRANSCRIPT_CONTENT).encode(),
            content_type='application/json',
        )
        response = self.client.post(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/',
            {
                'label': 'From file',
                'content_source': 'file',
                'content_file': json_file,
            },
        )

        transcript = Transcript.objects.get(
            uploaded_file=uploaded_file, label='From file'
        )
        # Content is normalized to the mmt-transcript format on ingestion.
        self.assertEqual(transcript.content['format'], 'mmt-transcript')
        self.assertEqual(transcript.content['version'], 1)
        self.assertTrue(transcript.content['segments'][0]['id'].startswith('seg_'))
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

    def test_create_transcript_post_invalid_format(self):
        """Pasted JSON without segments re-renders the form with an error."""
        self.client.login(username='alice', password='password')
        uploaded_file = self.uploaded_file
        response = self.client.post(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/',
            {
                'label': 'Invalid format',
                'content': '{}',
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(
            Transcript.objects.filter(
                uploaded_file=uploaded_file, label='Invalid format'
            ).exists()
        )
        self.assertContains(
            response, 'The transcript must contain a non-empty list of segments.'
        )

    def test_create_transcript_post_from_file_invalid_format(self):
        """Uploaded JSON without word timestamps re-renders the form with an error."""
        self.client.login(username='alice', password='password')
        uploaded_file = self.uploaded_file
        content = {
            'segments': [{'start': 0.0, 'end': 1.0, 'words': [{'word': 'Hello'}]}]
        }
        json_file = SimpleUploadedFile(
            'transcript.json',
            json.dumps(content).encode(),
            content_type='application/json',
        )
        response = self.client.post(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/',
            {
                'label': 'Invalid format',
                'content_source': 'file',
                'content_file': json_file,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(
            Transcript.objects.filter(
                uploaded_file=uploaded_file, label='Invalid format'
            ).exists()
        )
        self.assertContains(
            response,
            'Word 1 in segment 1 must have numeric start and end timestamps.',
        )

    def test_create_transcript_post_logged_out(self):
        """Transcript view redirects if logged out."""
        uploaded_file = self.uploaded_file
        response = self.client.post(
            f'/uploaded-files/{uploaded_file.id}/create-transcript/',
            {
                'label': 'Test transcript',
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
                'content': '{}',
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


@pytest.fixture
def incomplete_upload(db):
    """An upload with one chunk received and no assembled file.

    The user has no feature flags; tests that need chunked upload add the flag
    themselves.
    """
    user = User.objects.create_user(
        username='carol',
        password='password',
        email='carol@example.com',
        terms_accepted_version=1,
    )
    user.user_permissions.add(Permission.objects.get(codename='view_uploadedfile'))
    project = create_project(title='Test project', user=user)
    uploaded_file = UploadedFile.objects.create(
        project=project,
        filename='partial.mp4',
        original_filename='partial.mp4',
        media_type='video/mp4',
        size=2 * settings.MMT_UPLOAD_CHUNK_SIZE,
    )
    FileChunk.objects.create(uploaded_file=uploaded_file, index=0)
    return user, project, uploaded_file


def test_detail_links_to_project_upload_for_incomplete_file(client, incomplete_upload):
    """The incomplete-file hint is a note in the main column and links to the project upload page."""
    user, project, incomplete_file = incomplete_upload
    FeatureFlag.objects.create(user=user, name=FeatureFlag.Name.CHUNKED_UPLOAD)
    client.force_login(user)

    response = client.get(f'/uploaded-files/{incomplete_file.id}/')

    content = response.content.decode()
    assert f'/uploaded-files/{incomplete_file.id}/resume-upload/' not in content

    soup = BeautifulSoup(response.content, 'html.parser')
    notice = soup.find(attrs={'data-testid': 'incomplete-notice'})
    assert notice is not None
    assert 'note' in notice['class']
    assert notice.find_parent(class_='metadata') is None
    assert 'In order to resume the file' in notice.get_text()
    assert notice.find('a')['href'] == f'/projects/{project.id}/upload/'


def test_detail_omits_resume_hint_without_chunked_upload_flag(
    client, incomplete_upload
):
    """Without the flag there is no way to resume, so the hint is not offered."""
    user, _project, incomplete_file = incomplete_upload
    client.force_login(user)

    response = client.get(f'/uploaded-files/{incomplete_file.id}/')

    soup = BeautifulSoup(response.content, 'html.parser')
    assert soup.find(attrs={'data-testid': 'incomplete-notice'}) is None


@pytest.fixture
def video_upload(db):
    """A video upload whose original file exists on disk."""
    user = User.objects.create_user(
        username='dave',
        password='password',
        email='dave@example.com',
        terms_accepted_version=1,
    )
    user.user_permissions.add(Permission.objects.get(codename='view_uploadedfile'))
    project = create_project(title='Test project', user=user)
    uploaded_file = UploadedFile.objects.create(
        project=project,
        filename='recording.mov',
        original_filename='recording.mov',
        has_file=True,
        size=len(b'original bytes'),
        media_type='video/quicktime',
    )
    uploaded_file.file_path.write_bytes(b'original bytes')

    yield user, uploaded_file

    uploaded_file.file_path.unlink(missing_ok=True)
    uploaded_file.web_video_path.unlink(missing_ok=True)


def write_web_video(uploaded_file, content=b'web video bytes'):
    path = uploaded_file.web_video_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_stream_prefers_web_video_when_available(client, video_upload):
    """The derived web video is streamed when the flag is set and it exists."""
    user, uploaded_file = video_upload
    write_web_video(uploaded_file)
    UploadedFile.objects.filter(pk=uploaded_file.pk).update(has_web_video=True)
    client.force_login(user)

    response = client.get(f'/uploaded-files/{uploaded_file.id}/stream/')

    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == 'video/mp4'
    assert b''.join(response.streaming_content) == b'web video bytes'


def test_stream_serves_original_when_no_web_video(client, video_upload):
    """Without a derived web video the original is streamed with its type."""
    user, uploaded_file = video_upload
    client.force_login(user)

    response = client.get(f'/uploaded-files/{uploaded_file.id}/stream/')

    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == 'video/quicktime'
    assert b''.join(response.streaming_content) == b'original bytes'


def test_stream_falls_back_to_original_when_web_video_file_missing(
    client, video_upload
):
    """A set flag without the file on disk falls back to the original."""
    user, uploaded_file = video_upload
    UploadedFile.objects.filter(pk=uploaded_file.pk).update(has_web_video=True)
    client.force_login(user)

    response = client.get(f'/uploaded-files/{uploaded_file.id}/stream/')

    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == 'video/quicktime'
    assert b''.join(response.streaming_content) == b'original bytes'


@pytest.fixture
def corrupt_upload(db):
    """A complete video upload whose client and server checksums disagree."""
    user = User.objects.create_user(
        username='erin',
        password='password',
        email='erin@example.com',
        terms_accepted_version=1,
    )
    user.user_permissions.add(
        Permission.objects.get(codename='view_uploadedfile'),
        Permission.objects.get(codename='add_transcript'),
    )
    project = create_project(title='Test project', user=user)
    uploaded_file = UploadedFile.objects.create(
        project=project,
        filename='damaged.mp4',
        original_filename='damaged.mp4',
        has_file=True,
        size=20000,
        media_type='video/mp4',
        checksum_client='aaa',
        checksum_server='bbb',
    )
    return user, uploaded_file


def test_detail_omits_media_element_for_corrupt_file(client, corrupt_upload):
    """A corrupt file gets no player, because its bytes cannot be decoded reliably."""
    user, uploaded_file = corrupt_upload
    client.force_login(user)

    with mock.patch.object(UploadedFile, 'update_has_file_field'):
        response = client.get(f'/uploaded-files/{uploaded_file.id}/')

    soup = BeautifulSoup(response.content, 'html.parser')
    assert soup.find('video') is None
    assert soup.find('audio') is None


def test_detail_still_offers_download_for_corrupt_file(client, corrupt_upload):
    """The download link stays available so the file can be inspected locally."""
    user, uploaded_file = corrupt_upload
    client.force_login(user)

    with mock.patch.object(UploadedFile, 'update_has_file_field'):
        response = client.get(f'/uploaded-files/{uploaded_file.id}/')

    soup = BeautifulSoup(response.content, 'html.parser')
    download = soup.find('a', href=f'/uploaded-files/{uploaded_file.id}/download/')
    assert download is not None


def test_detail_reports_missing_before_corrupt(client, corrupt_upload):
    """A record whose file is gone from disk is missing; corruption is moot then.

    The view refreshes has_file from disk, so a mismatch recorded for a file
    that no longer exists does not turn into a corrupt status.
    """
    user, uploaded_file = corrupt_upload
    client.force_login(user)

    response = client.get(f'/uploaded-files/{uploaded_file.id}/')

    soup = BeautifulSoup(response.content, 'html.parser')
    assert soup.select_one('.pill--missing') is not None
    assert soup.find(attrs={'data-testid': 'corruption-warning'}) is None


def test_detail_omits_add_transcript_for_corrupt_file(client, corrupt_upload):
    """No transcript can be started, because it would run on bytes known to be wrong."""
    user, uploaded_file = corrupt_upload
    client.force_login(user)

    with mock.patch.object(UploadedFile, 'update_has_file_field'):
        response = client.get(f'/uploaded-files/{uploaded_file.id}/')

    soup = BeautifulSoup(response.content, 'html.parser')
    link = soup.find(
        'a', href=f'/uploaded-files/{uploaded_file.id}/create-transcript/'
    )
    assert link is None


def test_detail_shows_corruption_warning(client, corrupt_upload):
    """A corrupt file is named as such, so the user knows to re-upload it."""
    user, uploaded_file = corrupt_upload
    client.force_login(user)

    with mock.patch.object(UploadedFile, 'update_has_file_field'):
        response = client.get(f'/uploaded-files/{uploaded_file.id}/')

    soup = BeautifulSoup(response.content, 'html.parser')
    assert soup.find(attrs={'data-testid': 'corruption-warning'}) is not None


@pytest.mark.django_db
def test_detail_shows_processing_notice_carrying_the_poller(client):
    """A processing file gets a note in the main column, and the note drives the polling.

    The note and the poller share the same condition and the same lifetime, so
    the poller sits on the note rather than on an element of the metadata panel.
    """
    user = User.objects.create_user(
        username='dave',
        password='password',
        email='dave@example.com',
        terms_accepted_version=1,
    )
    user.user_permissions.add(Permission.objects.get(codename='view_uploadedfile'))
    project = create_project(title='Test project', user=user)
    processing_file = UploadedFile.objects.create(
        project=project,
        filename='processing.mp4',
        original_filename='processing.mp4',
        assembling=True,
        size=20000,
        media_type='video/mp4',
    )
    client.force_login(user)

    response = client.get(f'/uploaded-files/{processing_file.id}/')

    soup = BeautifulSoup(response.content, 'html.parser')
    notice = soup.find(attrs={'data-testid': 'processing-notice'})
    assert notice is not None
    assert 'note' in notice['class']
    assert notice.find_parent(class_='metadata') is None
    assert notice['x-data'] == (
        f"uploadStatusPoller('/uploaded-files/{processing_file.id}/status/')"
    )
