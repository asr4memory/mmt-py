from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import CHUNK_SIZE, FileChunk, UploadedFile
from mmt.uploaded_files.use_cases import upload_chunk

User = get_user_model()


class UploadChunkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )
        _, cls.project = create_project(title='Test project', user=cls.bob)
        cls.uploaded_file = UploadedFile.objects.create(
            filename='test_file.mp4',
            original_filename='test_file.mp4',
            media_type='video/mp4',
            project=cls.project,
            size=2 * CHUNK_SIZE,
        )

    def test_upload_chunk_invalid_index(self):
        """Raises ValueError for an index outside the valid range."""
        with self.assertRaises(ValueError):
            upload_chunk(self.uploaded_file, index=-1, data=b'data')

        with self.assertRaises(ValueError):
            upload_chunk(self.uploaded_file, index=2, data=b'data')

    def test_upload_chunk_idempotent(self):
        """If a chunk record already exists, skip it without creating a duplicate."""
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)

        upload_chunk(self.uploaded_file, index=0, data=b'data')

        self.assertEqual(self.uploaded_file.chunks.count(), 1)

    def test_upload_chunk_incomplete(self):
        """Chunk is stored; upload is not yet complete."""
        chunk_path = FileChunk(uploaded_file=self.uploaded_file, index=0).chunk_path
        self.addCleanup(chunk_path.unlink, missing_ok=True)

        complete = upload_chunk(self.uploaded_file, index=0, data=b'chunk data')

        self.assertFalse(complete)
        self.assertEqual(self.uploaded_file.chunks.count(), 1)

    @mock.patch('mmt.uploaded_files.use_cases.create_waveform_data')
    @mock.patch('mmt.uploaded_files.use_cases.calculate_server_checksum')
    @mock.patch.object(UploadedFile, 'assemble_chunks')
    def test_upload_chunk_complete(self, mock_assemble, mock_checksum, mock_waveform):
        """When the last chunk arrives, assembly and background tasks are triggered."""
        uploaded_file = UploadedFile.objects.create(
            filename='single_chunk.mp4',
            original_filename='single_chunk.mp4',
            media_type='video/mp4',
            project=self.project,
            size=CHUNK_SIZE,
        )
        chunk_path = FileChunk(uploaded_file=uploaded_file, index=0).chunk_path
        self.addCleanup(chunk_path.unlink, missing_ok=True)

        complete = upload_chunk(uploaded_file, index=0, data=b'chunk data')

        self.assertTrue(complete)
        mock_assemble.assert_called_once()
        mock_checksum.delay.assert_called_once_with(uploaded_file.id)
        mock_waveform.delay.assert_called_once_with(uploaded_file.id)

    @mock.patch('mmt.uploaded_files.use_cases.create_waveform_data')
    @mock.patch('mmt.uploaded_files.use_cases.calculate_server_checksum')
    @mock.patch.object(UploadedFile, 'assemble_chunks')
    def test_upload_chunk_skips_assembly_if_already_assembled(self, mock_assemble, mock_checksum, mock_waveform):
        """If has_file is already True when the lock is acquired, assembly is not repeated."""
        uploaded_file = UploadedFile.objects.create(
            filename='already_assembled.mp4',
            original_filename='already_assembled.mp4',
            media_type='video/mp4',
            project=self.project,
            size=CHUNK_SIZE,
            has_file=True,
        )
        chunk_path = FileChunk(uploaded_file=uploaded_file, index=0).chunk_path
        self.addCleanup(chunk_path.unlink, missing_ok=True)

        complete = upload_chunk(uploaded_file, index=0, data=b'chunk data')

        self.assertFalse(complete)
        mock_assemble.assert_not_called()
        mock_checksum.delay.assert_not_called()
        mock_waveform.delay.assert_not_called()
