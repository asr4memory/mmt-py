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
            filename='test_file.mp4', media_type='video/mp4', project=cls.project
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
        project = self.project
        uploaded_file = self.uploaded_file

        # Create file before it is deleted
        file_path = uploaded_file.file_path
        with open(file_path, 'w') as f:
            f.write('Just some dummy text.')

        self.assertTrue(file_path.exists())

        uploaded_file.delete_file()
        self.assertFalse(file_path.exists())

    def test_is_audio(self):
        actual = self.uploaded_file.is_audio()
        expected = False
        self.assertEqual(actual, expected)

    def test_is_video(self):
        actual = self.uploaded_file.is_video()
        expected = True
        self.assertEqual(actual, expected)

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


class FileChunkModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )
        _, cls.project = create_project(title='Test project', user=cls.bob)
        cls.uploaded_file = UploadedFile.objects.create(
            filename='test_file.mp4',
            media_type='video/mp4',
            project=cls.project,
            size=4 * CHUNK_SIZE,
        )

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
