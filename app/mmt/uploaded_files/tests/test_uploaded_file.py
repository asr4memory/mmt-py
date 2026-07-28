from pathlib import Path
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

from mmt.projects.models import Project
from mmt.projects.use_cases import create_project

from mmt.uploaded_files.models import FileChunk, UploadedFile, Waveform

User = get_user_model()


class UploadedFileModelTests(TestCase):
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
        chunk0.chunk_path.parent.mkdir(exist_ok=True)
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

    def test_status_missing_without_file_or_chunks(self):
        """Status is 'missing' when there is neither a file nor any chunks."""
        self.assertEqual(self.uploaded_file.status, 'missing')

    def test_status_incomplete_with_chunks(self):
        """Status is 'incomplete' while chunks are present but not yet assembled."""
        FileChunk.objects.create(uploaded_file=self.uploaded_file, index=0)
        self.assertEqual(self.uploaded_file.status, 'incomplete')

    def test_status_processing_while_assembling(self):
        """Status is 'processing' once assembly has been queued."""
        self.uploaded_file.assembling = True
        self.assertEqual(self.uploaded_file.status, 'processing')

    def test_status_complete_with_file(self):
        """Status is 'complete' once the file has been assembled."""
        self.uploaded_file.has_file = True
        self.assertEqual(self.uploaded_file.status, 'complete')


def test_is_video_true_for_application_ogg():
    """An Ogg container is treated as video."""
    uploaded_file = UploadedFile(media_type='application/ogg')

    assert uploaded_file.is_video() is True


def test_file_category_video():
    assert UploadedFile(media_type='video/mp4').file_category() == 'video'


def test_file_category_video_for_application_ogg():
    assert UploadedFile(media_type='application/ogg').file_category() == 'video'


def test_file_category_audio():
    assert UploadedFile(media_type='audio/mpeg').file_category() == 'audio'


def test_file_category_pdf():
    assert UploadedFile(media_type='application/pdf').file_category() == 'pdf'


def test_file_category_image():
    assert UploadedFile(media_type='image/png').file_category() == 'image'


def test_file_category_text():
    assert UploadedFile(media_type='text/plain').file_category() == 'text'


def test_file_category_falls_back_to_media_type():
    """An unrecognised type keeps its media type so no information is lost."""
    assert UploadedFile(media_type='application/zip').file_category() == 'application/zip'


@pytest.fixture
def video_upload(db):
    user = User.objects.create_user(
        username='carol', password='password', email='carol@example.com'
    )
    project = create_project(title='Test project', user=user)
    uploaded_file = UploadedFile.objects.create(
        project=project,
        filename='recording.mov',
        original_filename='recording.mov',
        has_file=True,
        media_type='video/quicktime',
    )
    uploaded_file.file_path.write_bytes(b'original bytes')

    yield uploaded_file

    uploaded_file.file_path.unlink(missing_ok=True)
    uploaded_file.web_video_path.unlink(missing_ok=True)


def test_delete_file_removes_web_video(video_upload):
    """The derived web video is removed together with the original."""
    web_video_path = video_upload.web_video_path
    web_video_path.parent.mkdir(parents=True, exist_ok=True)
    web_video_path.write_bytes(b'web video bytes')
    video_upload.has_web_video = True
    video_upload.save()

    video_upload.delete_file()

    assert not web_video_path.exists()


def test_delete_file_without_web_video(video_upload):
    """Deleting a file that has no derived web video does not raise."""
    video_upload.delete_file()

    assert not video_upload.file_path.exists()
