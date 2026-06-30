import requests
from celery import shared_task
from django.conf import settings

from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.models import Transcript
from mmt.transcripts.normalize import extract_mentions


@shared_task
def enrich_transcript(transcript_id: int) -> None:
    transcript = Transcript.objects.get(pk=transcript_id)

    response = requests.post(
        f'{settings.MMT_NER_API_URL}/enrich',
        json=transcript.content,
        timeout=300,
    )
    response.raise_for_status()

    # The service returns its flat ner_entity/word_group_index signal; turn it
    # into the canonical mentions model. Validation then guards against the
    # service drifting from mmt (e.g. dropping format/speakers): fail the task
    # loudly rather than store invalid content.
    content = validate_mmt_content(extract_mentions(response.json())).model_dump()

    Transcript.objects.create(
        uploaded_file=transcript.uploaded_file,
        label=f'{transcript.label} (NER)',
        language=transcript.language,
        content=content,
    )
