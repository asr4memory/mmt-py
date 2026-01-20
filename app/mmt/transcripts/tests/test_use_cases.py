from django.contrib.auth import get_user_model
from django.test import TestCase

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import UploadedFile
from mmt.transcripts.models import Transcript
from mmt.transcripts.use_cases import create_transcript, delete_transcript

User = get_user_model()


class TranscriptUseCaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )
        _, cls.project = create_project(title='Test project', user=cls.user)
        cls.uploaded_file = UploadedFile.objects.create(
            project=cls.project,
            filename='test_file.mp4',
            has_file=True,
            size=20000,
            transferred=20000,
            media_type='video/mp4',
        )

    def test_create_transcript_usecase_success(self):
        """create_transcript returns (True, transcript)."""
        success, transcript = create_transcript(
            label='Test transcript',
            language='en',
            content=dict(),
            uploaded_file=self.uploaded_file,
        )

        self.assertTrue(success)
        self.assertEqual(transcript.label, 'Test transcript')
        self.assertEqual(transcript.language, 'en')
        self.assertEqual(transcript.content, dict())
        self.assertEqual(transcript.uploaded_file_id, self.uploaded_file.id)
        self.assertIsNotNone(transcript.id)

    def test_create_transcript_usecase_failure(self):
        """create_transcript returns (False, None) if creation fails."""
        success, transcript = create_transcript()

        self.assertFalse(success)
        self.assertIsNone(transcript)

    def test_delete_transcript_usecase_success(self):
        """delete_transcript returns True if transcript has been deleted."""
        _, transcript = create_transcript(
            label='Test transcript', language='en', content=dict(), uploaded_file=self.uploaded_file,
        )

        success = delete_transcript(transcript)

        self.assertTrue(success)
        self.assertEqual(Transcript.objects.count(), 0)
