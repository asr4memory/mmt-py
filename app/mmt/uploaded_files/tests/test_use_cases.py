from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import FileChunk, UploadedFile
from mmt.uploaded_files.use_cases import upload_chunk

User = get_user_model()


class UploadChunkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )
        cls.project = create_project(title='Test project', user=cls.bob)
        cls.uploaded_file = UploadedFile.objects.create(
            filename='test_file.mp4',
            original_filename='test_file.mp4',
            media_type='video/mp4',
            project=cls.project,
            size=2 * settings.MMT_UPLOAD_CHUNK_SIZE,
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

    def test_upload_chunk_non_final_does_not_lock(self):
        """A non-final chunk returns without acquiring the parent row lock."""
        chunk_path = FileChunk(uploaded_file=self.uploaded_file, index=0).chunk_path
        self.addCleanup(chunk_path.unlink, missing_ok=True)

        with mock.patch.object(
            UploadedFile.objects,
            'select_for_update',
            wraps=UploadedFile.objects.select_for_update,
        ) as mock_lock:
            complete = upload_chunk(self.uploaded_file, index=0, data=b'chunk data')

        self.assertFalse(complete)
        mock_lock.assert_not_called()

    @mock.patch('mmt.uploaded_files.use_cases.task_assemble_chunks')
    def test_upload_chunk_final_takes_lock(self, mock_assemble):
        """The completing chunk acquires the row lock before queuing assembly."""
        chunk0 = FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        chunk0.chunk_path.parent.mkdir(exist_ok=True)
        chunk0.chunk_path.write_bytes(b'data')
        chunk1_path = FileChunk(uploaded_file=self.uploaded_file, index=1).chunk_path
        self.addCleanup(chunk0.chunk_path.unlink, missing_ok=True)
        self.addCleanup(chunk1_path.unlink, missing_ok=True)

        with (
            mock.patch.object(
                UploadedFile.objects,
                'select_for_update',
                wraps=UploadedFile.objects.select_for_update,
            ) as mock_lock,
            self.captureOnCommitCallbacks(execute=True),
        ):
            complete = upload_chunk(self.uploaded_file, index=1, data=b'more data')

        self.assertTrue(complete)
        mock_lock.assert_called_once()
        mock_assemble.delay.assert_called_once_with(self.uploaded_file.id)

    @mock.patch('mmt.uploaded_files.use_cases.task_assemble_chunks')
    def test_upload_chunk_complete(self, mock_assemble):
        """When the last chunk arrives, the file is marked assembling and assembly is queued."""
        uploaded_file = UploadedFile.objects.create(
            filename='single_chunk.mp4',
            original_filename='single_chunk.mp4',
            media_type='video/mp4',
            project=self.project,
            size=settings.MMT_UPLOAD_CHUNK_SIZE,
        )
        chunk_path = FileChunk(uploaded_file=uploaded_file, index=0).chunk_path
        self.addCleanup(chunk_path.unlink, missing_ok=True)

        with self.captureOnCommitCallbacks(execute=True):
            complete = upload_chunk(uploaded_file, index=0, data=b'chunk data')

        self.assertTrue(complete)
        uploaded_file.refresh_from_db()
        self.assertTrue(uploaded_file.assembling)
        self.assertFalse(uploaded_file.has_file)
        mock_assemble.delay.assert_called_once_with(uploaded_file.id)

    @mock.patch('mmt.uploaded_files.use_cases.task_assemble_chunks')
    def test_upload_chunk_skips_assembly_if_already_assembled(self, mock_assemble):
        """If has_file is already True when the lock is acquired, assembly is not queued."""
        uploaded_file = UploadedFile.objects.create(
            filename='already_assembled.mp4',
            original_filename='already_assembled.mp4',
            media_type='video/mp4',
            project=self.project,
            size=settings.MMT_UPLOAD_CHUNK_SIZE,
            has_file=True,
        )
        chunk_path = FileChunk(uploaded_file=uploaded_file, index=0).chunk_path
        self.addCleanup(chunk_path.unlink, missing_ok=True)

        with self.captureOnCommitCallbacks(execute=True):
            complete = upload_chunk(uploaded_file, index=0, data=b'chunk data')

        self.assertFalse(complete)
        mock_assemble.delay.assert_not_called()

    @mock.patch('mmt.uploaded_files.use_cases.task_assemble_chunks')
    def test_upload_chunk_skips_assembly_if_already_assembling(self, mock_assemble):
        """A final chunk arriving while assembly is already queued does not re-enqueue it."""
        uploaded_file = UploadedFile.objects.create(
            filename='assembling.mp4',
            original_filename='assembling.mp4',
            media_type='video/mp4',
            project=self.project,
            size=2 * settings.MMT_UPLOAD_CHUNK_SIZE,
            assembling=True,
        )
        chunk0 = FileChunk.objects.create(uploaded_file=uploaded_file, index=0)
        chunk0.chunk_path.parent.mkdir(exist_ok=True)
        chunk0.chunk_path.write_bytes(b'data')
        chunk1_path = FileChunk(uploaded_file=uploaded_file, index=1).chunk_path
        self.addCleanup(chunk0.chunk_path.unlink, missing_ok=True)
        self.addCleanup(chunk1_path.unlink, missing_ok=True)

        with self.captureOnCommitCallbacks(execute=True):
            complete = upload_chunk(uploaded_file, index=1, data=b'more data')

        self.assertFalse(complete)
        mock_assemble.delay.assert_not_called()
