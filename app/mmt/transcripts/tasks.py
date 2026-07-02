import copy

import requests
from celery import shared_task
from django.conf import settings

from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.models import Transcript
from mmt.transcripts.normalize import (
    apply_mention_spans,
    segment_batches,
    speaker_turn_batches,
)

BATCHERS = {
    'turns': speaker_turn_batches,
    'segments': segment_batches,
}


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
        language=transcript.language,
        content=content,
    )
