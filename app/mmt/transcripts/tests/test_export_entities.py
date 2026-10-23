import json

from mmt.transcripts.exporters import export_to_entities
from mmt.transcripts.normalize import normalize_content


def exported(transcript, duration=0):
    return json.loads(export_to_entities(transcript, duration=duration))


def test_linked_mentions_are_listed_under_their_entity(export_content):
    # Links the fixture's unlinked mention m2 to a new entity, widens it to two
    # words and adds a second mention of the same entity in another segment.
    export_content['entities']['e2'] = {
        'name': 'Bob',
        'type': 'PER',
        'wikidataId': 'Q123',
    }
    export_content['mentions']['m2']['entityId'] = 'e2'
    export_content['mentions']['m3'] = {'type': 'PER', 'score': 1.0, 'entityId': 'e2'}
    export_content['segments'][0]['words'][3]['mentionId'] = 'm2'
    export_content['segments'][2]['words'][1]['mentionId'] = 'm3'
    transcript = normalize_content(export_content)

    assert exported(transcript)['entities'] == [
        {
            'name': 'Bob',
            'type': 'PER',
            'wikidataId': 'Q123',
            'mentions': [
                {'start': 1.7, 'end': 4.2},
                {'start': 9.3, 'end': 10.0},
            ],
        },
    ]


def test_redacted_and_unlinked_mentions_are_left_out(export_transcript):
    # The only mention of e1 lies in redaction r1, and m2 has no entity, so no
    # entity has a mention to export.
    assert exported(export_transcript)['entities'] == []


def test_entity_without_mentions_is_left_out(export_content):
    export_content['entities']['e2'] = {
        'name': 'Bob',
        'type': 'PER',
        'wikidataId': None,
    }
    transcript = normalize_content(export_content)

    assert exported(transcript)['entities'] == []


def test_duration_is_null_when_unknown(export_transcript):
    assert exported(export_transcript, duration=0)['duration'] is None
    assert exported(export_transcript, duration=600)['duration'] == 600
