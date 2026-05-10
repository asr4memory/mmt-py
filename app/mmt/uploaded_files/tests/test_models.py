from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from mmt.projects.models import Project
from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import CHUNK_SIZE, FileChunk, UploadedFile, Waveform

User = get_user_model()


class UploadedFileModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )

        _, cls.project = create_project(title='Test project', user=cls.bob)

        cls.uploaded_file = UploadedFile.objects.create(
            filename='test_file.mp4', original_filename='test_file.mp4', media_type='video/mp4', project=cls.project
        )

    @mock.patch.object(Project, 'upload_directory', new_callable=mock.PropertyMock)
    def test_file_path(self, mock_project_upload_directory):
        """Returns project directory combined with filename."""
        mock_project_upload_directory.return_value = Path('test')

        actual = self.uploaded_file.file_path
        expected = Path('test/test_file.mp4')
        self.assertEqual(actual, expected)

    def test_delete_file(self):
        """Deletes uploaded file."""
        file_path = self.uploaded_file.file_path
        file_path.write_text('Just some dummy text.')
        self.addCleanup(file_path.unlink, missing_ok=True)

        self.uploaded_file.delete_file()

        self.assertFalse(file_path.exists())

    def test_delete_file_removes_chunk_files(self):
        """Also removes chunk files from disk when deleting."""
        file_path = self.uploaded_file.file_path
        file_path.write_text('dummy')
        self.addCleanup(file_path.unlink, missing_ok=True)

        chunk0 = FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        chunk1 = FileChunk.objects.create(uploaded_file=self.uploaded_file, index=1)
        chunk0.chunk_path.write_bytes(b'part0')
        chunk1.chunk_path.write_bytes(b'part1')
        self.addCleanup(chunk0.chunk_path.unlink, missing_ok=True)
        self.addCleanup(chunk1.chunk_path.unlink, missing_ok=True)

        self.uploaded_file.delete_file()

        self.assertFalse(chunk0.chunk_path.exists())
        self.assertFalse(chunk1.chunk_path.exists())

    def test_is_audio(self):
        actual = self.uploaded_file.is_audio()
        expected = False
        self.assertEqual(actual, expected)

    def test_is_video(self):
        actual = self.uploaded_file.is_video()
        expected = True
        self.assertEqual(actual, expected)

    def test_status_missing(self):
        self.assertEqual(self.uploaded_file.status, 'missing')

    def test_status_incomplete(self):
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        self.assertEqual(self.uploaded_file.status, 'incomplete')

    def test_status_complete(self):
        self.uploaded_file.has_file = True
        self.assertEqual(self.uploaded_file.status, 'complete')

    def test_has_waveform_negative(self):
        actual = self.uploaded_file.has_waveform
        expected = False
        self.assertEqual(actual, expected)

    def test_has_waveform_positive(self):
        Waveform.objects.create(
            uploaded_file=self.uploaded_file,
            data=[-1, 3, 5, -3, 2],
        )
        uploaded_file = UploadedFile.objects.get(pk=self.uploaded_file.pk)
        actual = uploaded_file.has_waveform
        expected = True
        self.assertEqual(actual, expected)

    def test_filename_altered_false_when_unchanged(self):
        f = UploadedFile(filename='file.mp4', original_filename='file.mp4')
        self.assertFalse(f.filename_altered)

    def test_filename_altered_true_when_changed(self):
        f = UploadedFile(filename='my_file.mp4', original_filename='my file.mp4')
        self.assertTrue(f.filename_altered)

    def test_assemble_chunks(self):
        """Assembles chunk files into final file and cleans up chunks."""
        chunk0 = FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        chunk1 = FileChunk.objects.create(uploaded_file=self.uploaded_file, index=1)
        chunk0.chunk_path.write_bytes(b'hello ')
        chunk1.chunk_path.write_bytes(b'world')
        self.addCleanup(self.uploaded_file.file_path.unlink, missing_ok=True)

        self.uploaded_file.assemble_chunks()

        self.assertEqual(self.uploaded_file.file_path.read_bytes(), b'hello world')
        self.assertFalse(chunk0.chunk_path.exists())
        self.assertFalse(chunk1.chunk_path.exists())
        self.assertEqual(self.uploaded_file.chunks.count(), 0)
        self.assertTrue(self.uploaded_file.has_file)

    def test_assemble_chunks_raises_if_chunks_missing(self):
        """Raises ValueError when not all expected chunks are present."""
        uploaded_file = UploadedFile.objects.create(
            filename='test_partial.mp4',
            original_filename='test_partial.mp4',
            media_type='video/mp4',
            project=self.project,
            size=2 * CHUNK_SIZE,
        )
        chunk0 = FileChunk.objects.create(uploaded_file=uploaded_file, index=0)
        chunk0.chunk_path.write_bytes(b'data')
        self.addCleanup(chunk0.chunk_path.unlink, missing_ok=True)

        with self.assertRaises(ValueError):
            uploaded_file.assemble_chunks()

    def test_assemble_chunks_cleans_up_on_failure(self):
        """If assembly fails, the temp file is removed and DB is left unchanged."""
        chunk0 = FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        chunk1 = FileChunk.objects.create(uploaded_file=self.uploaded_file, index=1)
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
        _, cls.project = create_project(title='Test project', user=cls.bob)
        # 2 full chunks + a partial last chunk of 500 bytes
        cls.uploaded_file = UploadedFile.objects.create(
            filename='partial.mp4',
            original_filename='partial.mp4',
            media_type='video/mp4',
            project=cls.project,
            size=2 * CHUNK_SIZE + 500,
        )

    def test_no_chunks(self):
        """Returns 0 when no chunks have been received."""
        self.assertEqual(self.uploaded_file.transferred_from_chunks(), 0)

    def test_full_chunk(self):
        """Counts a full-sized chunk correctly."""
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        self.assertEqual(self.uploaded_file.transferred_from_chunks(), CHUNK_SIZE)

    def test_partial_last_chunk(self):
        """Counts the last (partial) chunk by its actual size, not CHUNK_SIZE."""
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=2)
        self.assertEqual(self.uploaded_file.transferred_from_chunks(), 500)

    def test_all_chunks(self):
        """Sum equals total file size when all chunks are received."""
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=1)
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=2)
        self.assertEqual(
            self.uploaded_file.transferred_from_chunks(), 2 * CHUNK_SIZE + 500
        )


class FileChunkModelTests(TestCase):
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
            size=4 * CHUNK_SIZE,
        )

    @mock.patch('mmt.uploaded_files.models.generate_file_md5')
    def test_create_checksum(self, mock_md5):
        """Computes and stores MD5 checksum of the chunk file."""
        mock_md5.return_value = 'abc123'
        chunk = FileChunk(uploaded_file=self.uploaded_file, index=0)

        chunk.create_checksum()

        mock_md5.assert_called_once_with(chunk.chunk_path)
        self.assertEqual(chunk.checksum, 'abc123')

    @mock.patch.object(Project, 'upload_directory', new_callable=mock.PropertyMock)
    def test_chunk_path(self, mock_upload_directory):
        """Returns the final file path suffixed with .part.<index>."""
        mock_upload_directory.return_value = Path('test')
        chunk = FileChunk(uploaded_file=self.uploaded_file, index=3)

        self.assertEqual(chunk.chunk_path, Path('test/test_file.mp4.part.3'))

    def test_chunk_tracking(self):
        """Missing chunk indices are the difference between total and received."""
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=2)

        self.assertEqual(
            self.uploaded_file.missing_chunk_indices(),
            {1, 3},
        )
