from datetime import timedelta

import pytest
from django.utils import timezone

from mmt.jobs.tasks import task_delete_old_jobs
from mmt.transcripts.models import EntityExtractionJob, TranscriptionJob


def age(job, days):
    type(job).objects.filter(pk=job.pk).update(
        updated_at=timezone.now() - timedelta(days=days)
    )


@pytest.mark.parametrize(
    ('status', 'days', 'kept'),
    [
        (TranscriptionJob.SUCCEEDED, 31, False),
        (TranscriptionJob.FAILED, 31, False),
        (TranscriptionJob.SUCCEEDED, 29, True),
        (TranscriptionJob.PENDING, 31, True),
        (TranscriptionJob.SUBMITTED, 31, True),
        (TranscriptionJob.RUNNING, 31, True),
    ],
)
def test_delete_old_jobs_deletes_old_finished_transcription_jobs(
    alice, make_transcription_job, status, days, kept
):
    job = make_transcription_job(alice, status=status)
    age(job, days)

    task_delete_old_jobs()

    assert TranscriptionJob.objects.filter(pk=job.pk).exists() == kept


@pytest.mark.parametrize(
    ('status', 'days', 'kept'),
    [
        (EntityExtractionJob.SUCCEEDED, 31, False),
        (EntityExtractionJob.FAILED, 31, False),
        (EntityExtractionJob.SUCCEEDED, 29, True),
        (EntityExtractionJob.QUEUED, 31, True),
    ],
)
def test_delete_old_jobs_deletes_old_finished_extraction_jobs(
    alice, make_extraction_job, status, days, kept
):
    job = make_extraction_job(alice, status=status)
    age(job, days)

    task_delete_old_jobs()

    assert EntityExtractionJob.objects.filter(pk=job.pk).exists() == kept
