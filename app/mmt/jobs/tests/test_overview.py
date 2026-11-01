from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from mmt.jobs.overview import active_job_count, grouped_jobs
from mmt.transcripts.models import EntityExtractionJob, Transcript, TranscriptionJob


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
        (TranscriptionJob.PENDING, 'active'),
        (TranscriptionJob.SUBMITTED, 'active'),
        (TranscriptionJob.RUNNING, 'active'),
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
    assert len(jobs.active + jobs.finished) == 1


@pytest.mark.parametrize(
    ('status', 'group'),
    [
        (EntityExtractionJob.QUEUED, 'active'),
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
    assert len(jobs.active + jobs.finished) == 1


def test_active_jobs_list_running_before_pending_jobs_each_oldest_first(
    alice, make_transcription_job, make_extraction_job
):
    now = timezone.now()
    jobs = [
        make_transcription_job(alice, 'old_pending.mp4'),
        make_extraction_job(alice, 'new_pending'),
        make_transcription_job(
            alice, 'old_running.mp4', status=TranscriptionJob.SUBMITTED
        ),
        make_transcription_job(
            alice, 'new_running.mp4', status=TranscriptionJob.RUNNING
        ),
    ]
    ages = [timedelta(hours=4), timedelta(hours=3), timedelta(hours=2), timedelta(0)]
    for job, age in zip(jobs, ages, strict=True):
        type(job).objects.filter(pk=job.pk).update(created_at=now - age)

    assert subjects(group_jobs().active) == [
        'old_running.mp4',
        'new_running.mp4',
        'old_pending.mp4',
        'new_pending',
    ]


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


def test_a_succeeded_transcription_job_has_its_transcript_as_the_result(
    alice, make_transcription_job
):
    job = make_transcription_job(alice, status=TranscriptionJob.SUCCEEDED)
    transcript = Transcript.objects.create(
        uploaded_file=job.uploaded_file, label='Whisper transcript', content={}
    )
    job.transcript = transcript
    job.save()

    [row] = group_jobs().finished

    assert row.result_label == 'Whisper transcript'
    assert row.result_url == reverse('transcripts:detail', kwargs={'pk': transcript.pk})


def test_a_succeeded_extraction_job_has_its_result_transcript_as_the_result(
    alice, make_extraction_job
):
    job = make_extraction_job(alice, status=EntityExtractionJob.SUCCEEDED)
    result = Transcript.objects.create(
        uploaded_file=job.transcript.uploaded_file,
        label='Transcript with entities',
        content={},
    )
    job.result_transcript = result
    job.save()

    [row] = group_jobs().finished

    assert row.result_label == 'Transcript with entities'
    assert row.result_url == reverse('transcripts:detail', kwargs={'pk': result.pk})


def test_a_failed_job_has_its_error_and_no_result(
    alice, make_transcription_job, make_extraction_job
):
    make_transcription_job(
        alice, status=TranscriptionJob.FAILED, error='Service unreachable'
    )
    make_extraction_job(alice, status=EntityExtractionJob.FAILED, error='Timeout')

    rows = group_jobs().finished

    assert sorted(row.error for row in rows) == ['Service unreachable', 'Timeout']
    assert all(row.result_url is None for row in rows)


def test_the_active_job_count_includes_pending_and_running_jobs_of_both_models(
    alice, make_transcription_job, make_extraction_job
):
    make_transcription_job(alice, 'pending.mp4', status=TranscriptionJob.PENDING)
    make_transcription_job(alice, 'submitted.mp4', status=TranscriptionJob.SUBMITTED)
    make_transcription_job(alice, 'running.mp4', status=TranscriptionJob.RUNNING)
    make_transcription_job(alice, 'done.mp4', status=TranscriptionJob.SUCCEEDED)
    make_transcription_job(alice, 'broken.mp4', status=TranscriptionJob.FAILED)
    make_extraction_job(alice, 'queued', status=EntityExtractionJob.QUEUED)
    make_extraction_job(alice, 'done', status=EntityExtractionJob.SUCCEEDED)
    make_extraction_job(alice, 'broken', status=EntityExtractionJob.FAILED)

    count = active_job_count(
        TranscriptionJob.objects.all(), EntityExtractionJob.objects.all()
    )

    assert count == 4
