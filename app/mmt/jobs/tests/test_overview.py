from datetime import timedelta

import pytest
from django.utils import timezone

from mmt.jobs.overview import grouped_jobs
from mmt.transcripts.models import EntityExtractionJob, TranscriptionJob


def group_jobs(finished_limit=50):
    return grouped_jobs(
        TranscriptionJob.objects.all(),
        EntityExtractionJob.objects.all(),
        finished_limit=finished_limit,
    )


def subjects(rows):
    return [row.subject for row in rows]


@pytest.mark.parametrize(
    ('status', 'group'),
    [
        (TranscriptionJob.PENDING, 'pending'),
        (TranscriptionJob.SUBMITTED, 'running'),
        (TranscriptionJob.RUNNING, 'running'),
        (TranscriptionJob.SUCCEEDED, 'finished'),
        (TranscriptionJob.FAILED, 'finished'),
    ],
)
def test_a_transcription_job_is_grouped_by_its_status(
    alice, make_transcription_job, status, group
):
    make_transcription_job(alice, 'interview.mp4', status=status)

    jobs = group_jobs()

    assert subjects(getattr(jobs, group)) == ['interview.mp4']
    assert len(jobs.running + jobs.pending + jobs.finished) == 1


@pytest.mark.parametrize(
    ('status', 'group'),
    [
        (EntityExtractionJob.QUEUED, 'pending'),
        (EntityExtractionJob.SUCCEEDED, 'finished'),
        (EntityExtractionJob.FAILED, 'finished'),
    ],
)
def test_an_extraction_job_is_grouped_by_its_status(
    alice, make_extraction_job, status, group
):
    make_extraction_job(alice, 'Interview transcript', status=status)

    jobs = group_jobs()

    assert subjects(getattr(jobs, group)) == ['Interview transcript']
    assert len(jobs.running + jobs.pending + jobs.finished) == 1


def test_pending_jobs_are_listed_oldest_first(
    alice, make_transcription_job, make_extraction_job
):
    now = timezone.now()
    newer = make_transcription_job(alice, 'newer.mp4')
    older = make_extraction_job(alice, 'older')
    TranscriptionJob.objects.filter(pk=newer.pk).update(created_at=now)
    EntityExtractionJob.objects.filter(pk=older.pk).update(
        created_at=now - timedelta(hours=1)
    )

    assert subjects(group_jobs().pending) == ['older', 'newer.mp4']


def test_running_jobs_are_listed_oldest_first(alice, make_transcription_job):
    now = timezone.now()
    newer = make_transcription_job(alice, 'newer.mp4', status=TranscriptionJob.RUNNING)
    older = make_transcription_job(
        alice, 'older.mp4', status=TranscriptionJob.SUBMITTED
    )
    TranscriptionJob.objects.filter(pk=newer.pk).update(created_at=now)
    TranscriptionJob.objects.filter(pk=older.pk).update(
        created_at=now - timedelta(hours=1)
    )

    assert subjects(group_jobs().running) == ['older.mp4', 'newer.mp4']


def test_finished_jobs_are_listed_newest_first_and_cut_to_the_limit(
    alice, make_transcription_job, make_extraction_job
):
    now = timezone.now()
    oldest = make_transcription_job(alice, 'oldest.mp4', status=TranscriptionJob.FAILED)
    middle = make_extraction_job(alice, 'middle', status=EntityExtractionJob.SUCCEEDED)
    newest = make_transcription_job(
        alice, 'newest.mp4', status=TranscriptionJob.SUCCEEDED
    )
    TranscriptionJob.objects.filter(pk=oldest.pk).update(
        updated_at=now - timedelta(hours=2)
    )
    EntityExtractionJob.objects.filter(pk=middle.pk).update(
        updated_at=now - timedelta(hours=1)
    )
    TranscriptionJob.objects.filter(pk=newest.pk).update(updated_at=now)

    assert subjects(group_jobs(finished_limit=2).finished) == ['newest.mp4', 'middle']
