from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from mmt.jobs.overview import FINISHED_EXTRACTION, FINISHED_TRANSCRIPTION
from mmt.transcripts.models import EntityExtractionJob, TranscriptionJob


@shared_task
def task_delete_old_jobs() -> None:
    """Delete finished jobs last updated more than MMT_JOB_RETENTION_DAYS ago."""
    cutoff = timezone.now() - timedelta(days=settings.MMT_JOB_RETENTION_DAYS)
    TranscriptionJob.objects.filter(
        status__in=FINISHED_TRANSCRIPTION, updated_at__lt=cutoff
    ).delete()
    EntityExtractionJob.objects.filter(
        status__in=FINISHED_EXTRACTION, updated_at__lt=cutoff
    ).delete()
