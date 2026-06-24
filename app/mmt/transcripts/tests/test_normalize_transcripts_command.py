from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


def whisper_content():
    return {
        'segments': [
            {
                'start': 0,
                'end': 1,
                'text': 'Hello',
                'speaker': 'SPEAKER_00',
                'words': [
                    {'start': 0, 'end': 1, 'word': 'Hello', 'speaker': 'SPEAKER_00'}
                ],
            }
        ]
    }


class NormalizeTranscriptsCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user(
            username='alice',
            password='password',
            email='alice@example.com',
            terms_accepted_version=1,
        )
        project = create_project(title='Test project', user=user)
        cls.uploaded_file = UploadedFile.objects.create(
            project=project,
            filename='test_file.mp4',
            original_filename='test_file.mp4',
            has_file=True,
            size=20000,
            media_type='video/mp4',
        )

    def make_transcript(self, content, label='T'):
        return Transcript.objects.create(
            label=label,
            language='en',
            content=content,
            uploaded_file=self.uploaded_file,
        )

    def call(self, *args):
        out = StringIO()
        err = StringIO()
        call_command('normalize_transcripts', *args, stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    def test_upgrades_legacy_whisper_content(self):
        transcript = self.make_transcript(whisper_content())
        self.call()
        transcript.refresh_from_db()
        self.assertEqual(transcript.content['format'], 'mmt-transcript')
        self.assertEqual(transcript.content['version'], 1)
        segment = transcript.content['segments'][0]
        self.assertTrue(segment['id'].startswith('seg_'))
        self.assertEqual(len(transcript.content['speakers']), 1)

    def test_idempotent_preserves_ids(self):
        transcript = self.make_transcript(whisper_content())
        self.call()
        transcript.refresh_from_db()
        first = transcript.content

        self.call()
        transcript.refresh_from_db()
        second = transcript.content

        self.assertEqual(first['speakers'][0]['id'], second['speakers'][0]['id'])
        self.assertEqual(first['segments'][0]['id'], second['segments'][0]['id'])

    def test_dry_run_does_not_save(self):
        transcript = self.make_transcript(whisper_content())
        out, _ = self.call('--dry-run')
        transcript.refresh_from_db()
        self.assertNotIn('format', transcript.content)
        self.assertIn('would', out.lower())

    def test_invalid_content_is_skipped_and_reported(self):
        good = self.make_transcript(whisper_content(), label='good')
        bad = self.make_transcript({}, label='bad')

        _, err = self.call()

        good.refresh_from_db()
        bad.refresh_from_db()
        self.assertEqual(good.content['format'], 'mmt-transcript')
        self.assertEqual(bad.content, {})
        self.assertIn(str(bad.pk), err)

    def test_reports_processed_count(self):
        self.make_transcript(whisper_content())
        self.make_transcript(whisper_content())
        out, _ = self.call()
        self.assertIn('2', out)
