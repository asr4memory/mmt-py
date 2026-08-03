from datetime import UTC, datetime
from unittest import mock

import pytest
import requests
from django.contrib.auth import get_user_model

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript, TranscriptionJob
from mmt.transcripts.tasks import (
    task_submit_transcription_job,
    task_sweep_transcription_jobs,
)
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()

# What the service returns from GET /jobs/{id}/result: whisperX output as-is.
WHISPER_RESULT = {
    'language': 'de',
    'segments': [
        {
            'start': 0.0,
            'end': 1.0,
            'text': 'Guten Tag',
            'speaker': 'SPEAKER_00',
            'words': [
                {'word': 'Guten', 'start': 0.0, 'end': 0.5, 'score': 0.97},
                {'word': 'Tag', 'start': 0.5, 'end': 1.0, 'score': 0.91},
            ],
        }
    ],
}

STARTED_AT = '2026-07-08T14:05:03+00:00'
FINISHED_AT = '2026-07-08T14:35:47+00:00'


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=''):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f'{self.status_code} error')


def status_response(status, **fields):
    body = {
        'id': 'j_8f3ab2c1',
        'status': status,
        'progress': 0.0,
        'created_at': '2026-07-08T14:02:11+00:00',
        'started_at': None,
        'finished_at': None,
        'language': 'de',
        'error': None,
    }
    body.update(fields)
    return FakeResponse(json_data=body)


@pytest.fixture
def uploaded_file(db):
    user = User.objects.create_user(
        username='bob', password='password', email='bob@example.com'
    )
    project = create_project(title='Test project', user=user)
    return UploadedFile.objects.create(
        filename='interview.mp4', media_type='video/mp4', project=project
    )


@pytest.fixture
def job(uploaded_file):
    return TranscriptionJob.objects.create(
        uploaded_file=uploaded_file, language='de', diarize=True
    )


@pytest.fixture
def submitted_job(job):
    job.asr_job_id = 'j_8f3ab2c1'
    job.status = TranscriptionJob.SUBMITTED
    job.save()
    return job


def test_submit_posts_the_relative_path_and_stores_the_job_id(job):
    response = FakeResponse(
        status_code=202, json_data={'id': 'j_8f3ab2c1', 'status': 'queued'}
    )

    with mock.patch(
        'mmt.transcripts.tasks.requests.post', return_value=response
    ) as post:
        task_submit_transcription_job(job.pk)

    body = post.call_args.kwargs['json']
    assert body['path'] == job.media_path
    assert body['language'] == 'de'
    assert body['diarize'] is True

    job.refresh_from_db()
    assert job.asr_job_id == 'j_8f3ab2c1'
    assert job.status == TranscriptionJob.SUBMITTED


def test_submit_omits_an_empty_language(job):
    job.language = ''
    job.save()
    response = FakeResponse(
        status_code=202, json_data={'id': 'j_8f3ab2c1', 'status': 'queued'}
    )

    with mock.patch(
        'mmt.transcripts.tasks.requests.post', return_value=response
    ) as post:
        task_submit_transcription_job(job.pk)

    assert 'language' not in post.call_args.kwargs['json']


def test_submit_marks_the_job_failed_on_a_rejected_path(job):
    response = FakeResponse(
        status_code=400, text='{"detail":"Path does not exist: bob/interview.mp4"}'
    )

    with mock.patch('mmt.transcripts.tasks.requests.post', return_value=response):
        task_submit_transcription_job(job.pk)

    job.refresh_from_db()
    assert job.status == TranscriptionJob.FAILED
    assert job.error == '{"detail":"Path does not exist: bob/interview.mp4"}'
    assert job.asr_job_id == ''


def test_sweep_copies_progress_and_timestamps(submitted_job):
    response = status_response(
        'running', progress=0.65, started_at=STARTED_AT, finished_at=None
    )

    with mock.patch('mmt.transcripts.tasks.requests.get', return_value=response) as get:
        task_sweep_transcription_jobs()

    assert get.call_args.args[0].endswith('/jobs/j_8f3ab2c1')

    submitted_job.refresh_from_db()
    assert submitted_job.status == TranscriptionJob.RUNNING
    assert submitted_job.progress == 0.65
    assert submitted_job.started_at == datetime(2026, 7, 8, 14, 5, 3, tzinfo=UTC)
    assert submitted_job.finished_at is None


def test_sweep_ingests_a_succeeded_job(submitted_job):
    responses = [
        status_response(
            'succeeded', progress=1.0, started_at=STARTED_AT, finished_at=FINISHED_AT
        ),
        FakeResponse(json_data=WHISPER_RESULT),
    ]

    with mock.patch('mmt.transcripts.tasks.requests.get', side_effect=responses) as get:
        task_sweep_transcription_jobs()

    assert get.call_args_list[1].args[0].endswith('/jobs/j_8f3ab2c1/result')

    submitted_job.refresh_from_db()
    assert submitted_job.status == TranscriptionJob.SUCCEEDED
    assert submitted_job.progress == 1.0
    assert submitted_job.started_at == datetime(2026, 7, 8, 14, 5, 3, tzinfo=UTC)
    assert submitted_job.finished_at == datetime(2026, 7, 8, 14, 35, 47, tzinfo=UTC)

    transcript = submitted_job.transcript
    assert transcript is not None
    assert transcript.uploaded_file == submitted_job.uploaded_file
    assert transcript.content['format'] == 'mmt-transcript'
    assert transcript.content['segments'][0]['words'][0]['word'] == 'Guten'


def test_sweep_stores_the_detected_language_in_the_content(submitted_job):
    responses = [
        status_response(
            'succeeded', progress=1.0, started_at=STARTED_AT, finished_at=FINISHED_AT
        ),
        FakeResponse(json_data=WHISPER_RESULT),
    ]

    with mock.patch('mmt.transcripts.tasks.requests.get', side_effect=responses):
        task_sweep_transcription_jobs()

    submitted_job.refresh_from_db()
    assert submitted_job.transcript.content['language'] == 'de'


def test_sweep_records_invalid_content_as_a_failure(submitted_job):
    responses = [
        status_response(
            'succeeded', progress=1.0, started_at=STARTED_AT, finished_at=FINISHED_AT
        ),
        FakeResponse(json_data={'language': 'de', 'segments': []}),
    ]

    with mock.patch('mmt.transcripts.tasks.requests.get', side_effect=responses):
        task_sweep_transcription_jobs()

    submitted_job.refresh_from_db()
    assert submitted_job.status == TranscriptionJob.FAILED
    assert submitted_job.error.startswith('ValidationError: ')
    assert submitted_job.transcript is None
    assert Transcript.objects.count() == 0


def test_sweep_records_a_failed_job(submitted_job):
    response = status_response(
        'failed',
        error='RuntimeError: CUDA out of memory',
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
    )

    with mock.patch('mmt.transcripts.tasks.requests.get', return_value=response):
        task_sweep_transcription_jobs()

    submitted_job.refresh_from_db()
    assert submitted_job.status == TranscriptionJob.FAILED
    assert submitted_job.error == 'RuntimeError: CUDA out of memory'
    assert submitted_job.started_at == datetime(2026, 7, 8, 14, 5, 3, tzinfo=UTC)
    assert submitted_job.finished_at == datetime(2026, 7, 8, 14, 35, 47, tzinfo=UTC)


def test_sweep_fails_on_404(submitted_job):
    with mock.patch(
        'mmt.transcripts.tasks.requests.get',
        return_value=FakeResponse(status_code=404),
    ) as get:
        task_sweep_transcription_jobs()

    assert get.call_count == 1

    submitted_job.refresh_from_db()
    assert submitted_job.status == TranscriptionJob.FAILED
    assert submitted_job.error == 'The transcription service does not know this job.'


def test_sweep_leaves_terminal_jobs_untouched(uploaded_file):
    for status in (TranscriptionJob.SUCCEEDED, TranscriptionJob.FAILED):
        TranscriptionJob.objects.create(
            uploaded_file=uploaded_file, asr_job_id='j_1', status=status
        )

    with mock.patch('mmt.transcripts.tasks.requests.get') as get:
        task_sweep_transcription_jobs()

    get.assert_not_called()


def test_sweep_continues_after_a_request_error(uploaded_file):
    first = TranscriptionJob.objects.create(
        uploaded_file=uploaded_file,
        asr_job_id='j_first',
        status=TranscriptionJob.SUBMITTED,
    )
    second = TranscriptionJob.objects.create(
        uploaded_file=uploaded_file,
        asr_job_id='j_second',
        status=TranscriptionJob.SUBMITTED,
    )

    def get_response(url, **kwargs):
        if 'j_first' in url:
            raise requests.ConnectionError('service unreachable')
        return status_response('running', progress=0.4, started_at=STARTED_AT)

    with mock.patch('mmt.transcripts.tasks.requests.get', side_effect=get_response):
        task_sweep_transcription_jobs()

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status == TranscriptionJob.SUBMITTED
    assert second.status == TranscriptionJob.RUNNING
    assert second.progress == 0.4
