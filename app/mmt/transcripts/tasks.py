import copy

import requests
from celery import shared_task
from django.conf import settings

from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.models import Transcript
from mmt.transcripts.normalize import apply_mention_spans, speaker_turn_batches


@shared_task
def enrich_transcript(transcript_id: int) -> None:
    transcript = Transcript.objects.get(pk=transcript_id)

    # The NER service is format-agnostic: it sees one word batch per speaker
    # turn and returns word-index entity spans, nothing transcript-shaped.
    batches = [
        [word['word'] for word in turn]
        for turn in speaker_turn_batches(transcript.content)
    ]
    response = requests.post(
        f'{settings.MMT_NER_API_URL}/extract',
        json={'batches': batches},
        timeout=300,
    )
    response.raise_for_status()

    # Merge the spans into a copy of the original content. Strict validation
    # before persisting: fail the task loudly rather than store invalid
    # content.
    content = apply_mention_spans(
        copy.deepcopy(transcript.content), response.json()['results']
    )
    content = validate_mmt_content(content).model_dump()

    Transcript.objects.create(
        uploaded_file=transcript.uploaded_file,
        label=f'{transcript.label} (NER)',
        language=transcript.language,
        content=content,
    )
