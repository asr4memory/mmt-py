import copy
import logging

import requests
from celery import shared_task
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime

from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.models import Transcript, TranscriptionJob
from mmt.transcripts.normalize import (
    apply_mention_spans,
    normalize_content,
    segment_batches,
    speaker_turn_batches,
)
from mmt.transcripts.validators import validate_whisper_input

logger = logging.getLogger(__name__)

BATCHERS = {
    'turns': speaker_turn_batches,
    'segments': segment_batches,
}

UNKNOWN_JOB_ERROR = 'The transcription service does not know this job.'


@shared_task
def enrich_transcript(transcript_id: int, batching: str = 'turns') -> None:
    transcript = Transcript.objects.get(pk=transcript_id)

    # Batches are built from the copy that is mutated below, so the merge
    # writes through the very word dicts the request was built from.
    content = copy.deepcopy(transcript.content)
    batches = BATCHERS[batching](content)

    # The NER service is format-agnostic: it sees word batches and returns
    # word-index entity spans, nothing transcript-shaped.
    response = requests.post(
        f'{settings.MMT_NER_API_URL}/extract',
        json={'batches': [[word['word'] for word in batch] for batch in batches]},
        timeout=300,
    )
    response.raise_for_status()

    # Strict validation before persisting: fail the task loudly rather than
    # store invalid content.
    content = apply_mention_spans(content, response.json()['results'], batches)
    content = validate_mmt_content(content).model_dump()

    Transcript.objects.create(
        uploaded_file=transcript.uploaded_file,
        label=f'{transcript.label} (NER, {batching})',
        content=content,
    )


@shared_task
def submit_transcription_job(job_id: int) -> None:
    """Hand a pending job to the ASR service.

    A 400 means the service rejected the path; that is a permanent condition,
    so the job is marked failed with the service's response body. Any other
    error status raises, so Celery records the failure. The sweep does not
    resubmit pending jobs, so a lost submission stays visible as pending.
    """
    job = TranscriptionJob.objects.get(pk=job_id)

    body = {'path': job.media_path, 'diarize': job.diarize}
    if job.language:
        body['language'] = job.language

    response = requests.post(
        f'{settings.MMT_ASR_API_URL}/jobs',
        json=body,
        timeout=30,
    )

    if response.status_code == 400:
        job.status = TranscriptionJob.FAILED
        job.error = response.text
        job.save()
        return

    response.raise_for_status()

    job.asr_job_id = response.json()['id']
    job.status = TranscriptionJob.SUBMITTED
    job.save()


@shared_task
def sweep_transcription_jobs() -> None:
    """Poll every non-terminal job once.

    Scheduled by Celery beat. Each job is handled on its own, so one
    unreachable service or one malformed response does not stop the sweep for
    the remaining jobs.
    """
    jobs = TranscriptionJob.objects.filter(status__in=TranscriptionJob.IN_PROGRESS)

    for job in jobs:
        try:
            _poll_job(job)
        except Exception:
            logger.exception('Polling transcription job %s failed', job.pk)


def _poll_job(job: TranscriptionJob) -> None:
    response = requests.get(
        f'{settings.MMT_ASR_API_URL}/jobs/{job.asr_job_id}',
        timeout=30,
    )

    # The service keeps its spool on a persistent volume, so a job it does not
    # know was removed or the volume was reset. The user re-runs it by
    # submitting a new transcription.
    if response.status_code == 404:
        job.status = TranscriptionJob.FAILED
        job.error = UNKNOWN_JOB_ERROR
        job.save()
        return

    response.raise_for_status()
    status = response.json()

    if status['status'] == 'queued':
        job.progress = status['progress']
        job.save()
        return

    job.started_at = _parse_time(status['started_at'])
    job.finished_at = _parse_time(status['finished_at'])

    if status['status'] == 'running':
        job.progress = status['progress']
        job.status = TranscriptionJob.RUNNING
    elif status['status'] == 'failed':
        job.error = status['error'] or ''
        job.status = TranscriptionJob.FAILED
    elif status['status'] == 'succeeded':
        result = requests.get(
            f'{settings.MMT_ASR_API_URL}/jobs/{job.asr_job_id}/result',
            timeout=300,
        )
        result.raise_for_status()
        _ingest_result(job, result.json())

    job.save()


def _ingest_result(job: TranscriptionJob, result: dict) -> None:
    """Store a finished transcription as a Transcript.

    Takes the same path as a manual whisperX upload: lenient input validation,
    then conversion to mmt content. The detected language is part of that
    content, so no language is set here. Sets the job's fields; the caller
    saves the job.
    """
    try:
        validate_whisper_input(result)
        content = normalize_content(result).model_dump()
    except ValidationError as exc:
        job.status = TranscriptionJob.FAILED
        job.error = f'{type(exc).__name__}: {exc}'
        return

    job.transcript = Transcript.objects.create(
        uploaded_file=job.uploaded_file,
        label='ASR',
        content=content,
    )
    job.status = TranscriptionJob.SUCCEEDED
    job.progress = 1.0


def _parse_time(value: str | None):
    return parse_datetime(value) if value else None
