from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from mmt.projects.use_cases import create_project
from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.models import EntityExtractionJob, Transcript
from mmt.transcripts.tasks import (
    enrich_transcript,
    mark_extraction_failed,
    store_entities,
)
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()

ORIGINAL_CONTENT = {
    'format': 'mmt-transcript',
    'version': 1,
    'language': 'en',
    'speakers': [],
    'entities': {},
    'redactions': {},
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

# Three segments, two speakers: seg_1/seg_2 share spk_a (one turn), seg_3
# is spk_b — so 2 turn batches but 3 segment batches.
TURNS_CONTENT = {
    'format': 'mmt-transcript',
    'version': 1,
    'speakers': [
        {'id': 'spk_a', 'name': 'A', 'color': '#5b9bd5'},
        {'id': 'spk_b', 'name': 'B', 'color': '#70ad47'},
    ],
    'entities': {},
    'redactions': {},
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


# What the NER worker returns: one word-index span list per batch.
EXTRACT_RESULTS = [[{'start': 0, 'end': 1, 'label': 'PER', 'score': 0.93}]]


@pytest.fixture
def uploaded_file(db):
    user = User.objects.create_user(
        username='alice', password='password', email='alice@example.com'
    )
    project = create_project(title='Test project', user=user)
    return UploadedFile.objects.create(
        filename='interview.mp3', media_type='audio/mpeg', project=project
    )


@pytest.fixture
def transcript(uploaded_file):
    return Transcript.objects.create(
        uploaded_file=uploaded_file, label='Interview', content=ORIGINAL_CONTENT
    )


@pytest.fixture
def job(transcript):
    return EntityExtractionJob.objects.create(transcript=transcript)


@pytest.fixture
def send_task():
    with mock.patch('mmt.transcripts.tasks.celery_app.send_task') as send_task:
        yield send_task


def test_enrich_transcript_creates_a_queued_job_and_sends_the_task(
    transcript, send_task
):
    enrich_transcript(transcript.pk)

    job = EntityExtractionJob.objects.get()
    assert job.transcript == transcript
    assert job.status == EntityExtractionJob.QUEUED
    send_task.assert_called_once()
    args, kwargs = send_task.call_args
    assert args == ('ner.extract',)
    assert kwargs['args'] == [[['Hello', 'world']]]
    assert kwargs['queue'] == 'ner'
    assert kwargs['task_id'] == str(job.task_id)
    link = kwargs['link']
    assert link.task == store_entities.name
    assert link.args == (job.pk, ORIGINAL_CONTENT)
    assert link.options['queue'] == 'celery'
    link_error = kwargs['link_error']
    assert link_error.task == mark_extraction_failed.name
    assert link_error.args == (job.pk,)
    assert link_error.immutable
    assert link_error.options['queue'] == 'celery'


def test_enrich_transcript_batches_by_speaker_turn(uploaded_file, send_task):
    """Consecutive same-speaker segments are sent as one flattened batch."""
    transcript = Transcript.objects.create(
        uploaded_file=uploaded_file, label='Turns', content=TURNS_CONTENT
    )

    enrich_transcript(transcript.pk)

    assert send_task.call_args.kwargs['args'] == [
        [['Hello', 'Angela', 'Merkel', 'here'], ['Bye']]
    ]


def test_store_entities_creates_the_enriched_transcript(transcript, job):
    store_entities(EXTRACT_RESULTS, job.pk, ORIGINAL_CONTENT)

    job.refresh_from_db()
    enriched = job.result_transcript
    assert job.status == EntityExtractionJob.SUCCEEDED
    assert Transcript.objects.count() == 2
    # Content is persisted as canonical mmt: each span is materialised into a
    # mention the covered words point at. Mention ids are minted, so the test
    # asserts the structure rather than an exact dict.
    assert enriched.content == validate_mmt_content(enriched.content).model_dump()
    mentions = enriched.content['mentions']
    assert [(m['type'], m['score']) for m in mentions.values()] == [('PER', 0.93)]
    [mention_id] = mentions
    words = enriched.content['segments'][0]['words']
    assert words[0]['mentionId'] == mention_id
    assert words[1]['mentionId'] is None
    assert enriched.uploaded_file == transcript.uploaded_file
    assert enriched.content['language'] == 'en'
    assert enriched.label == 'Interview (NER)'


def test_store_entities_maps_a_span_across_segments_of_one_turn(job):
    """A span crossing a segment boundary becomes one cross-segment mention."""
    results = [
        # "Angela Merkel" crosses the seg_1/seg_2 boundary.
        [{'start': 1, 'end': 3, 'label': 'PER', 'score': 0.92}],
        [],
    ]

    store_entities(results, job.pk, TURNS_CONTENT)

    job.refresh_from_db()
    content = job.result_transcript.content
    [mention_id] = content['mentions']
    first_turn_words = content['segments'][0]['words'] + content['segments'][1]['words']
    assert [w['mentionId'] for w in first_turn_words] == [
        None,
        mention_id,
        mention_id,
        None,
    ]


def test_store_entities_twice_for_one_job_creates_one_transcript(job):
    store_entities(EXTRACT_RESULTS, job.pk, ORIGINAL_CONTENT)
    store_entities(EXTRACT_RESULTS, job.pk, ORIGINAL_CONTENT)

    assert Transcript.objects.count() == 2


def test_store_entities_with_invalid_spans_fails_the_job(job):
    invalid = [[{'start': 0, 'end': 1, 'label': 'NOPE', 'score': 0.9}]]

    with pytest.raises(ValidationError):
        store_entities(invalid, job.pk, ORIGINAL_CONTENT)

    job.refresh_from_db()
    assert Transcript.objects.count() == 1
    assert job.status == EntityExtractionJob.FAILED
    assert job.error.startswith('ValidationError: ')


def test_mark_extraction_failed_stores_the_exception(job):
    with mock.patch('mmt.transcripts.tasks.AsyncResult') as async_result:
        async_result.return_value.result = RuntimeError('out of memory')
        mark_extraction_failed(job.pk)

    async_result.assert_called_once_with(str(job.task_id))
    job.refresh_from_db()
    assert job.status == EntityExtractionJob.FAILED
    assert job.error == 'RuntimeError: out of memory'


def test_mark_extraction_failed_leaves_a_succeeded_job_unchanged(job):
    job.status = EntityExtractionJob.SUCCEEDED
    job.save()

    with mock.patch('mmt.transcripts.tasks.AsyncResult') as async_result:
        async_result.return_value.result = RuntimeError('out of memory')
        mark_extraction_failed(job.pk)

    job.refresh_from_db()
    assert job.status == EntityExtractionJob.SUCCEEDED
    assert job.error == ''
