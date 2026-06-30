import copy
from unittest import mock

import requests
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase

from mmt.projects.use_cases import create_project
from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.models import Transcript
from mmt.transcripts.tasks import enrich_transcript
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()

ORIGINAL_CONTENT = {
    'format': 'mmt-transcript',
    'version': 1,
    'speakers': [],
    'segments': [
        {
            'id': 'seg_1',
            'start': 0.0,
            'end': 1.0,
            'text': 'Hello world',
            'speakerId': None,
            'words': [
                {'id': 'wrd_1', 'word': 'Hello', 'start': 0.0, 'end': 0.5, 'score': 0.9},
                {'id': 'wrd_2', 'word': 'world', 'start': 0.5, 'end': 1.0, 'score': 0.8},
            ],
        }
    ],
}

# What the NER service returns: the same mmt content with ner_entity filled in.
ENRICHED_CONTENT = {
    'format': 'mmt-transcript',
    'version': 1,
    'speakers': [],
    'segments': [
        {
            'id': 'seg_1',
            'start': 0.0,
            'end': 1.0,
            'text': 'Hello world',
            'speakerId': None,
            'words': [
                {
                    'id': 'wrd_1',
                    'word': 'Hello',
                    'start': 0.0,
                    'end': 0.5,
                    'score': 0.9,
                    'ner_entity': 'PER',
                },
                {'id': 'wrd_2', 'word': 'world', 'start': 0.5, 'end': 1.0, 'score': 0.8},
            ],
        }
    ],
}


def _mock_response(json_data):
    response = mock.Mock()
    # Real requests builds a fresh dict per .json() call; mirror that so the
    # task's in-place mention extraction can't mutate the shared fixture.
    response.json.side_effect = lambda: copy.deepcopy(json_data)
    response.raise_for_status.return_value = None
    return response


class EnrichTranscriptTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user(
            username='alice', password='password', email='alice@example.com'
        )
        project = create_project(title='Test project', user=user)
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
        # Content is persisted as canonical mmt: the flat ner_entity signal is
        # materialised into a mention the tagged word points at. (Mention ids
        # are minted, so assert structure rather than an exact dict.)
        self.assertEqual(enriched.content, validate_mmt_content(enriched.content).model_dump())
        mentions = enriched.content['mentions']
        self.assertEqual([m['label'] for m in mentions], ['PER'])
        words = enriched.content['segments'][0]['words']
        self.assertEqual(words[0]['ner_mention_id'], mentions[0]['id'])
        self.assertIsNone(words[1]['ner_mention_id'])
        self.assertEqual(enriched.uploaded_file, self.uploaded_file)
        self.assertEqual(enriched.language, self.transcript.language)
        self.assertEqual(enriched.label, 'Interview (NER)')

    def test_raises_on_invalid_enriched_content(self):
        """A response that drifted from mmt (here: format/speakers stripped)
        must fail the task loudly rather than persist invalid content."""
        invalid = {'segments': ENRICHED_CONTENT['segments']}
        with mock.patch(
            'mmt.transcripts.tasks.requests.post',
            return_value=_mock_response(invalid),
        ):
            with self.assertRaises(DjangoValidationError):
                enrich_transcript(self.transcript.pk)

        self.assertEqual(Transcript.objects.count(), 1)

    def test_posts_original_content_to_api(self):
        with mock.patch('mmt.transcripts.tasks.requests.post') as mock_post:
            mock_post.return_value = _mock_response(ENRICHED_CONTENT)
            enrich_transcript(self.transcript.pk)

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json'], ORIGINAL_CONTENT)

    def test_raises_on_http_error(self):
        error_response = mock.Mock()
        error_response.raise_for_status.side_effect = requests.HTTPError(
            '500 Server Error'
        )

        with mock.patch(
            'mmt.transcripts.tasks.requests.post', return_value=error_response
        ):
            with self.assertRaises(requests.HTTPError):
                enrich_transcript(self.transcript.pk)

        self.assertEqual(Transcript.objects.count(), 1)
