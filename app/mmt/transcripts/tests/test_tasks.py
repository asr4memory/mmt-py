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
    'language': 'en',
    'speakers': [],
    'segments': [
        {
            'id': 'seg_1',
            'start': 0.0,
            'end': 1.0,
            'speakerId': None,
            'words': [
                {
                    'id': 'wrd_1',
                    'word': 'Hello',
                    'start': 0.0,
                    'end': 0.5,
                    'score': 0.9,
                },
                {
                    'id': 'wrd_2',
                    'word': 'world',
                    'start': 0.5,
                    'end': 1.0,
                    'score': 0.8,
                },
            ],
        }
    ],
}

# What the NER service returns: one word-index span list per batch.
EXTRACT_RESPONSE = {
    'results': [[{'start': 0, 'end': 1, 'label': 'PER', 'score': 0.93}]]
}

# Three segments, two speakers: seg_1/seg_2 share spk_a (one turn), seg_3
# is spk_b — so 2 turn batches but 3 segment batches.
TURNS_CONTENT = {
    'format': 'mmt-transcript',
    'version': 1,
    'speakers': [
        {'id': 'spk_a', 'name': 'A', 'color': '#5b9bd5'},
        {'id': 'spk_b', 'name': 'B', 'color': '#70ad47'},
    ],
    'segments': [
        {
            'id': 'seg_1',
            'start': 0.0,
            'end': 1.0,
            'speakerId': 'spk_a',
            'words': [
                {
                    'id': 'wrd_1',
                    'word': 'Hello',
                    'start': 0.0,
                    'end': 0.4,
                    'score': 0.9,
                    'speakerId': 'spk_a',
                },
                {
                    'id': 'wrd_2',
                    'word': 'Angela',
                    'start': 0.5,
                    'end': 1.0,
                    'score': 0.9,
                    'speakerId': 'spk_a',
                },
            ],
        },
        {
            'id': 'seg_2',
            'start': 1.0,
            'end': 2.0,
            'speakerId': 'spk_a',
            'words': [
                {
                    'id': 'wrd_3',
                    'word': 'Merkel',
                    'start': 1.0,
                    'end': 1.5,
                    'score': 0.9,
                    'speakerId': 'spk_a',
                },
                {
                    'id': 'wrd_4',
                    'word': 'here',
                    'start': 1.5,
                    'end': 2.0,
                    'score': 0.9,
                    'speakerId': 'spk_a',
                },
            ],
        },
        {
            'id': 'seg_3',
            'start': 2.0,
            'end': 3.0,
            'speakerId': 'spk_b',
            'words': [
                {
                    'id': 'wrd_5',
                    'word': 'Bye',
                    'start': 2.0,
                    'end': 3.0,
                    'score': 0.9,
                    'speakerId': 'spk_b',
                },
            ],
        },
    ],
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
        project = create_project(title='Test project', user=user)
        cls.uploaded_file = UploadedFile.objects.create(
            filename='interview.mp3', media_type='audio/mpeg', project=project
        )
        cls.transcript = Transcript.objects.create(
            uploaded_file=cls.uploaded_file,
            label='Interview',
            content=ORIGINAL_CONTENT,
        )

    def test_creates_new_transcript_with_enriched_content(self):
        with mock.patch(
            'mmt.transcripts.tasks.requests.post',
            return_value=_mock_response(EXTRACT_RESPONSE),
        ):
            enrich_transcript(self.transcript.pk)

        self.assertEqual(Transcript.objects.count(), 2)
        enriched = Transcript.objects.exclude(pk=self.transcript.pk).get()
        # Content is persisted as canonical mmt: each span is materialised
        # into a mention the covered words point at. (Mention ids are minted,
        # so assert structure rather than an exact dict.)
        self.assertEqual(
            enriched.content, validate_mmt_content(enriched.content).model_dump()
        )
        mentions = enriched.content['mentions']
        # The span's real confidence lands as the mention score.
        self.assertEqual(
            [(m['label'], m['score']) for m in mentions.values()], [('PER', 0.93)]
        )
        words = enriched.content['segments'][0]['words']
        [mention_id] = mentions
        self.assertEqual(words[0]['mentionId'], mention_id)
        self.assertIsNone(words[1]['mentionId'])
        self.assertEqual(enriched.uploaded_file, self.uploaded_file)
        # The language lives in the content, so it rides along with it.
        self.assertEqual(enriched.content['language'], 'en')
        # The batching mode lands in the label so results from different
        # modes are distinguishable.
        self.assertEqual(enriched.label, 'Interview (NER, turns)')

    def test_does_not_mutate_original_transcript_content(self):
        with mock.patch(
            'mmt.transcripts.tasks.requests.post',
            return_value=_mock_response(EXTRACT_RESPONSE),
        ):
            enrich_transcript(self.transcript.pk)

        self.transcript.refresh_from_db()
        self.assertEqual(self.transcript.content, ORIGINAL_CONTENT)

    def test_raises_on_invalid_merged_content(self):
        """Spans the schema rejects (here: an unknown label) must fail the
        task loudly rather than persist invalid content."""
        invalid = {'results': [[{'start': 0, 'end': 1, 'label': 'NOPE', 'score': 0.9}]]}
        with (
            mock.patch(
                'mmt.transcripts.tasks.requests.post',
                return_value=_mock_response(invalid),
            ),
            self.assertRaises(DjangoValidationError),
        ):
            enrich_transcript(self.transcript.pk)

        self.assertEqual(Transcript.objects.count(), 1)

    def test_posts_word_batches_to_extract(self):
        with mock.patch('mmt.transcripts.tasks.requests.post') as mock_post:
            mock_post.return_value = _mock_response(EXTRACT_RESPONSE)
            enrich_transcript(self.transcript.pk)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertTrue(args[0].endswith('/extract'))
        self.assertEqual(kwargs['json'], {'batches': [['Hello', 'world']]})

    def test_batches_by_speaker_turn(self):
        """Consecutive same-speaker segments are posted as one flattened
        batch; a span crossing the segment boundary becomes one
        cross-segment mention."""
        transcript = Transcript.objects.create(
            uploaded_file=self.uploaded_file,
            label='Turns',
            content=TURNS_CONTENT,
        )
        response = {
            'results': [
                # "Angela Merkel" crosses the seg_1/seg_2 boundary.
                [{'start': 1, 'end': 3, 'label': 'PER', 'score': 0.92}],
                [],
            ]
        }
        with mock.patch('mmt.transcripts.tasks.requests.post') as mock_post:
            mock_post.return_value = _mock_response(response)
            enrich_transcript(transcript.pk)

        self.assertEqual(
            mock_post.call_args.kwargs['json'],
            {'batches': [['Hello', 'Angela', 'Merkel', 'here'], ['Bye']]},
        )
        enriched = Transcript.objects.exclude(
            pk__in=[self.transcript.pk, transcript.pk]
        ).get()
        [mention_id] = enriched.content['mentions']
        first_turn_words = (
            enriched.content['segments'][0]['words']
            + enriched.content['segments'][1]['words']
        )
        self.assertEqual(
            [w['mentionId'] for w in first_turn_words],
            [None, mention_id, mention_id, None],
        )

    def test_segment_batching_posts_one_batch_per_segment(self):
        transcript = Transcript.objects.create(
            uploaded_file=self.uploaded_file,
            label='Turns',
            content=TURNS_CONTENT,
        )
        response = {
            'results': [
                [],
                # Segment-relative index: "Merkel" is word 0 of seg_2.
                [{'start': 0, 'end': 1, 'label': 'PER', 'score': 0.92}],
                [],
            ]
        }
        with mock.patch('mmt.transcripts.tasks.requests.post') as mock_post:
            mock_post.return_value = _mock_response(response)
            enrich_transcript(transcript.pk, batching='segments')

        self.assertEqual(
            mock_post.call_args.kwargs['json'],
            {'batches': [['Hello', 'Angela'], ['Merkel', 'here'], ['Bye']]},
        )
        enriched = Transcript.objects.exclude(
            pk__in=[self.transcript.pk, transcript.pk]
        ).get()
        self.assertEqual(enriched.label, 'Turns (NER, segments)')
        [mention_id] = enriched.content['mentions']
        self.assertEqual(
            enriched.content['segments'][1]['words'][0]['mentionId'], mention_id
        )
        self.assertIsNone(enriched.content['segments'][0]['words'][1]['mentionId'])

    def test_unknown_batching_mode_raises(self):
        with mock.patch('mmt.transcripts.tasks.requests.post') as mock_post:
            with self.assertRaises(KeyError):
                enrich_transcript(self.transcript.pk, batching='bogus')

        mock_post.assert_not_called()
        self.assertEqual(Transcript.objects.count(), 1)

    def test_raises_on_http_error(self):
        error_response = mock.Mock()
        error_response.raise_for_status.side_effect = requests.HTTPError(
            '500 Server Error'
        )

        with (
            mock.patch(
                'mmt.transcripts.tasks.requests.post', return_value=error_response
            ),
            self.assertRaises(requests.HTTPError),
        ):
            enrich_transcript(self.transcript.pk)

        self.assertEqual(Transcript.objects.count(), 1)
