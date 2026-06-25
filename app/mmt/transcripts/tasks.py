import requests
from celery import shared_task
from django.conf import settings

from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.models import Transcript


@shared_task
def enrich_transcript(transcript_id: int) -> None:
    transcript = Transcript.objects.get(pk=transcript_id)

    response = requests.post(
        f'{settings.MMT_NER_API_URL}/enrich',
        json=transcript.content,
        timeout=300,
    )
    response.raise_for_status()

    # Guard against the NER service drifting from mmt (e.g. dropping
    # format/speakers): fail the task loudly rather than store invalid content.
    content = validate_mmt_content(response.json()).model_dump()

    Transcript.objects.create(
        uploaded_file=transcript.uploaded_file,
        label=f'{transcript.label} (NER)',
        language=transcript.language,
        content=content,
    )
