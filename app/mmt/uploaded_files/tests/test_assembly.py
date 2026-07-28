from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from mmt.projects.models import Project
from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import FileChunk, UploadedFile

User = get_user_model()


class AssembleChunksTests(TestCase):
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
        )

    def test_queryset_partial_returns_only_incomplete_uploads(self):
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        complete = UploadedFile.objects.create(
            filename='complete.mp4',
            media_type='video/mp4',
            project=self.project,
            has_file=True,
        )
        assembling = UploadedFile.objects.create(
            filename='assembling.mp4',
            media_type='video/mp4',
            project=self.project,
            assembling=True,
        )
        FileChunk.objects.create(uploaded_file=assembling, index=0)
        missing = UploadedFile.objects.create(
            filename='missing.mp4',
            media_type='video/mp4',
            project=self.project,
        )

        partial = UploadedFile.objects.partial()

        self.assertIn(self.uploaded_file, partial)
        self.assertNotIn(complete, partial)
        self.assertNotIn(assembling, partial)
        self.assertNotIn(missing, partial)

    def test_assemble_chunks(self):
        """Assembles chunk files into final file and cleans up chunks."""
        self.uploaded_file.assembling = True
        self.uploaded_file.save(update_fields=['assembling'])
        chunk0 = FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        chunk1 = FileChunk.objects.create(uploaded_file=self.uploaded_file, index=1)
        chunk0.chunk_path.parent.mkdir(exist_ok=True)
        chunk0.chunk_path.write_bytes(b'hello ')
        chunk1.chunk_path.write_bytes(b'world')
        self.addCleanup(self.uploaded_file.file_path.unlink, missing_ok=True)

        self.uploaded_file.assemble_chunks()

        self.assertEqual(self.uploaded_file.file_path.read_bytes(), b'hello world')
        self.assertFalse(chunk0.chunk_path.exists())
        self.assertFalse(chunk1.chunk_path.exists())
        self.assertEqual(self.uploaded_file.chunks.count(), 0)
        self.assertTrue(self.uploaded_file.has_file)
        self.assertFalse(self.uploaded_file.assembling)

    def test_assemble_chunks_raises_if_chunks_missing(self):
        """Raises ValueError when not all expected chunks are present."""
        uploaded_file = UploadedFile.objects.create(
            filename='test_partial.mp4',
            original_filename='test_partial.mp4',
            media_type='video/mp4',
            project=self.project,
            size=2 * settings.MMT_UPLOAD_CHUNK_SIZE,
        )
        chunk0 = FileChunk.objects.create(uploaded_file=uploaded_file, index=0)
        chunk0.chunk_path.parent.mkdir(exist_ok=True)
        chunk0.chunk_path.write_bytes(b'data')
        self.addCleanup(chunk0.chunk_path.unlink, missing_ok=True)

        with self.assertRaises(ValueError):
            uploaded_file.assemble_chunks()

    def test_assemble_chunks_cleans_up_on_failure(self):
        """If assembly fails, the temp file is removed and DB is left unchanged."""
        chunk0 = FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        chunk1 = FileChunk.objects.create(uploaded_file=self.uploaded_file, index=1)
        chunk0.chunk_path.parent.mkdir(exist_ok=True)
        chunk0.chunk_path.write_bytes(b'hello ')
        # chunk1 has no file on disk — read_bytes() will raise FileNotFoundError
        tmp_path = self.uploaded_file.file_path.with_name(
            self.uploaded_file.file_path.name + '.tmp'
        )
        self.addCleanup(chunk0.chunk_path.unlink, missing_ok=True)
        self.addCleanup(tmp_path.unlink, missing_ok=True)

        with self.assertRaises(FileNotFoundError):
            self.uploaded_file.assemble_chunks()

        self.assertFalse(tmp_path.exists())
        self.assertFalse(self.uploaded_file.file_path.exists())
        self.assertEqual(self.uploaded_file.chunks.count(), 2)
        self.assertFalse(self.uploaded_file.has_file)


class TransferredFromChunksTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username='bob2', password='password', email='bob2@example.com'
        )
        cls.project = create_project(title='Test project', user=cls.bob)
        # 2 full chunks + a partial last chunk of 500 bytes
        cls.uploaded_file = UploadedFile.objects.create(
            filename='partial.mp4',
            original_filename='partial.mp4',
            media_type='video/mp4',
            project=cls.project,
            size=2 * settings.MMT_UPLOAD_CHUNK_SIZE + 500,
        )

    def test_no_chunks(self):
        """Returns 0 when no chunks have been received."""
        self.assertEqual(self.uploaded_file.transferred_from_chunks(), 0)

    def test_full_chunk(self):
        """Counts a full-sized chunk correctly."""
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        self.assertEqual(
            self.uploaded_file.transferred_from_chunks(), settings.MMT_UPLOAD_CHUNK_SIZE
        )

    def test_partial_last_chunk(self):
        """Counts the last (partial) chunk by its actual size, not MMT_UPLOAD_CHUNK_SIZE."""
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=2)
        self.assertEqual(self.uploaded_file.transferred_from_chunks(), 500)

    def test_all_chunks(self):
        """Sum equals total file size when all chunks are received."""
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=1)
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=2)
        self.assertEqual(
            self.uploaded_file.transferred_from_chunks(),
            2 * settings.MMT_UPLOAD_CHUNK_SIZE + 500,
        )


class FileChunkModelTests(TestCase):
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
            size=4 * settings.MMT_UPLOAD_CHUNK_SIZE,
        )

    @mock.patch.object(Project, 'upload_directory', new_callable=mock.PropertyMock)
    def test_chunk_path(self, mock_upload_directory):
        """Returns the final file path suffixed with .part.<index>."""
        mock_upload_directory.return_value = Path('test')
        chunk = FileChunk(uploaded_file=self.uploaded_file, index=3)

        self.assertEqual(chunk.chunk_path, Path('test/chunks/test_file.mp4.part.3'))

    def test_chunk_tracking(self):
        """Missing chunk indices are the difference between total and received."""
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=2)

        self.assertEqual(
            self.uploaded_file.missing_chunk_indices(),
            {1, 3},
        )
