from django.conf import settings
from django.test import TestCase

from mmt.projects.forms import UploadedFileForm


class UploadedFileFormTests(TestCase):
    def test_valid_audio(self):
        form = UploadedFileForm(
            {'filename': 'recording.mp3', 'content_type': 'audio/mpeg', 'size': 20000}
        )
        self.assertTrue(form.is_valid())

    def test_valid_video(self):
        form = UploadedFileForm(
            {'filename': 'video.mp4', 'content_type': 'video/mp4', 'size': 20000}
        )
        self.assertTrue(form.is_valid())

    def test_valid_image(self):
        form = UploadedFileForm(
            {'filename': 'photo.jpg', 'content_type': 'image/jpeg', 'size': 20000}
        )
        self.assertTrue(form.is_valid())

    def test_valid_mxf(self):
        form = UploadedFileForm(
            {'filename': 'clip.mxf', 'content_type': 'application/mxf', 'size': 20000}
        )
        self.assertTrue(form.is_valid())

    def test_valid_mts(self):
        form = UploadedFileForm(
            {'filename': 'clip.mts', 'content_type': 'model/vnd.mts', 'size': 20000}
        )
        self.assertTrue(form.is_valid())

    def test_filename_empty(self):
        form = UploadedFileForm(
            {'filename': '', 'content_type': 'video/mp4', 'size': 20000}
        )
        self.assertFalse(form.is_valid())
        self.assertIn('filename', form.errors)

    def test_size_zero(self):
        form = UploadedFileForm(
            {'filename': 'video.mp4', 'content_type': 'video/mp4', 'size': 0}
        )
        self.assertFalse(form.is_valid())
        self.assertIn('size', form.errors)

    def test_size_negative(self):
        form = UploadedFileForm(
            {'filename': 'video.mp4', 'content_type': 'video/mp4', 'size': -1}
        )
        self.assertFalse(form.is_valid())
        self.assertIn('size', form.errors)

    def test_size_exceeds_maximum(self):
        form = UploadedFileForm(
            {
                'filename': 'video.mp4',
                'content_type': 'video/mp4',
                'size': settings.MMT_MAX_UPLOAD_SIZE + 1,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('size', form.errors)

    def test_size_at_maximum(self):
        form = UploadedFileForm(
            {
                'filename': 'video.mp4',
                'content_type': 'video/mp4',
                'size': settings.MMT_MAX_UPLOAD_SIZE,
            }
        )
        self.assertTrue(form.is_valid())

    def test_content_type_not_accepted(self):
        form = UploadedFileForm(
            {'filename': 'doc.pdf', 'content_type': 'application/pdf', 'size': 20000}
        )
        self.assertFalse(form.is_valid())
        self.assertIn('content_type', form.errors)

    def test_missing_fields(self):
        form = UploadedFileForm({})
        self.assertFalse(form.is_valid())
        self.assertIn('filename', form.errors)
        self.assertIn('content_type', form.errors)
        self.assertIn('size', form.errors)
