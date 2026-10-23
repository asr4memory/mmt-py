"""Export the linked entities with the timecodes of their mentions."""

import json

from mmt.transcripts.mmt_schema import Transcript


def export_to_entities(transcript: Transcript, *, duration: int) -> bytes:
    """Entities that have at least one exported mention, in stored order.

    A mention is exported when it is linked to an entity and none of its words
    is redacted. A duration of 0 means unknown and is written as null.
    """
    mention_words = {}
    for segment in transcript.segments:
        for word in segment.words:
            if word.mentionId is not None:
                mention_words.setdefault(word.mentionId, []).append(word)

    mentions_by_entity = {}
    for mention_id, words in mention_words.items():
        entity_id = transcript.mentions[mention_id].entityId
        if entity_id is None:
            continue
        if any(word.redactionId is not None for word in words):
            continue
        mentions_by_entity.setdefault(entity_id, []).append(
            {'start': words[0].start, 'end': words[-1].end}
        )

    entities = [
        {
            'name': entity.name,
            'type': entity.type,
            'wikidataId': entity.wikidataId,
            'mentions': mentions_by_entity[entity_id],
        }
        for entity_id, entity in transcript.entities.items()
        if entity_id in mentions_by_entity
    ]

    document = {'duration': duration or None, 'entities': entities}
    return json.dumps(document, ensure_ascii=False, indent=2).encode('utf-8')
