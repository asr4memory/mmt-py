"""The jobs of both job models, converted to one row type and grouped by state.

The row type exists because transcription and entity extraction jobs are two
models with different status values.
"""

from dataclasses import dataclass
from datetime import datetime

from django.db.models import QuerySet
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from mmt.transcripts.models import EntityExtractionJob, TranscriptionJob


@dataclass(frozen=True)
class JobRow:
    kind: str
    subject: str
    url: str
    status_display: str
    pill_modifier: str
    progress_percent: int | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class GroupedJobs:
    running: list[JobRow]
    pending: list[JobRow]
    finished: list[JobRow]


FINISHED_TRANSCRIPTION = (TranscriptionJob.SUCCEEDED, TranscriptionJob.FAILED)
FINISHED_EXTRACTION = (EntityExtractionJob.SUCCEEDED, EntityExtractionJob.FAILED)


def grouped_jobs(
    transcription_jobs: QuerySet[TranscriptionJob],
    entity_extraction_jobs: QuerySet[EntityExtractionJob],
    finished_limit: int = 50,
) -> GroupedJobs:
    """Group the given jobs into running, pending and the most recent finished."""
    transcription_jobs = transcription_jobs.select_related('uploaded_file')
    entity_extraction_jobs = entity_extraction_jobs.select_related(
        'transcript__uploaded_file'
    ).defer('transcript__content')

    running = [
        _transcription_row(job)
        for job in transcription_jobs.filter(status__in=TranscriptionJob.IN_PROGRESS)
    ]
    pending = [
        _transcription_row(job)
        for job in transcription_jobs.filter(status=TranscriptionJob.PENDING)
    ] + [
        _extraction_row(job)
        for job in entity_extraction_jobs.filter(status=EntityExtractionJob.QUEUED)
    ]
    # Each model contributes at most finished_limit jobs, so the merged list
    # contains the most recent finished_limit jobs of both.
    finished = [
        _transcription_row(job)
        for job in transcription_jobs.filter(
            status__in=FINISHED_TRANSCRIPTION
        ).order_by('-updated_at')[:finished_limit]
    ] + [
        _extraction_row(job)
        for job in entity_extraction_jobs.filter(
            status__in=FINISHED_EXTRACTION
        ).order_by('-updated_at')[:finished_limit]
    ]

    return GroupedJobs(
        running=sorted(running, key=lambda row: row.created_at),
        pending=sorted(pending, key=lambda row: row.created_at),
        finished=sorted(finished, key=lambda row: row.updated_at, reverse=True)[
            :finished_limit
        ],
    )


def _transcription_row(job: TranscriptionJob) -> JobRow:
    return JobRow(
        kind=_('Transcription'),
        subject=job.uploaded_file.display_name,
        url=reverse('uploaded_files:detail', kwargs={'pk': job.uploaded_file_id}),
        status_display=job.get_status_display(),
        pill_modifier=job.pill_modifier,
        progress_percent=job.progress_percent if job.is_in_progress else None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _extraction_row(job: EntityExtractionJob) -> JobRow:
    return JobRow(
        kind=_('Entity extraction'),
        subject=job.transcript.label,
        url=reverse('transcripts:detail', kwargs={'pk': job.transcript_id}),
        status_display=job.get_status_display(),
        pill_modifier=job.pill_modifier,
        progress_percent=None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
