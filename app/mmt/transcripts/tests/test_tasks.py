from unittest import mock

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript
from mmt.transcripts.tasks import enrich_transcript
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()

ORIGINAL_CONTENT = {
    'segments': [
        {
            'start': 0.0,
            'end': 1.0,
            'text': 'Hello world',
            'words': [
                {'word': 'Hello', 'start': 0.0, 'end': 0.5, 'score': 0.9},
                {'word': 'world', 'start': 0.5, 'end': 1.0, 'score': 0.8},
            ],
        }
    ]
}

ENRICHED_CONTENT = {
    'segments': [
        {
            'start': 0.0,
            'end': 1.0,
            'text': 'Hello world',
            'words': [
                {'word': 'Hello', 'start': 0.0, 'end': 0.5, 'score': 0.9, 'ner_entity': 'PER'},
                {'word': 'world', 'start': 0.5, 'end': 1.0, 'score': 0.8},
            ],
        }
    ]
}


def _mock_response(json_data):
    response = mock.Mock()
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


class EnrichTranscriptTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user(
            username='alice', password='password', email='alice@example.com'
        )
        _, project = create_project(title='Test project', user=user)
        cls.uploaded_file = UploadedFile.objects.create(
            filename='interview.mp3', media_type='audio/mpeg', project=project
        )
        cls.transcript = Transcript.objects.create(
            uploaded_file=cls.uploaded_file,
            label='Interview',
            language='en',
            content=ORIGINAL_CONTENT,
        )

    def test_creates_new_transcript_with_enriched_content(self):
        with mock.patch(
            'mmt.transcripts.tasks.requests.post',
            return_value=_mock_response(ENRICHED_CONTENT),
        ):
            enrich_transcript(self.transcript.pk)

        self.assertEqual(Transcript.objects.count(), 2)
        enriched = Transcript.objects.exclude(pk=self.transcript.pk).get()
        self.assertEqual(enriched.content, ENRICHED_CONTENT)
        self.assertEqual(enriched.uploaded_file, self.uploaded_file)
        self.assertEqual(enriched.language, self.transcript.language)
        self.assertEqual(enriched.label, 'Interview (NER)')

    def test_posts_original_content_to_api(self):
        with mock.patch('mmt.transcripts.tasks.requests.post') as mock_post:
            mock_post.return_value = _mock_response(ENRICHED_CONTENT)
            enrich_transcript(self.transcript.pk)

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json'], ORIGINAL_CONTENT)

    def test_raises_on_http_error(self):
        error_response = mock.Mock()
        error_response.raise_for_status.side_effect = requests.HTTPError('500 Server Error')

        with mock.patch('mmt.transcripts.tasks.requests.post', return_value=error_response):
            with self.assertRaises(requests.HTTPError):
                enrich_transcript(self.transcript.pk)

        self.assertEqual(Transcript.objects.count(), 1)
