from datetime import datetime

from django.utils import timezone

ASR = 'ASR'
NER = 'NER'


def transcript_label(process: str, created_at: datetime) -> str:
    """Return the label of a transcript that a job of the given process creates.

    The time is the creation time of the job, in the configured time zone.
    """
    local = timezone.localtime(created_at)
    return f'{process} ({local:%Y-%m-%d %H:%M})'
