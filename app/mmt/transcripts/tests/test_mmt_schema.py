import pytest
from django.core.exceptions import ValidationError

from mmt.transcripts.mmt_schema import validate_mmt_content


def valid_content():
    return {
        'format': 'mmt-transcript',
        'version': 1,
        'speakers': [{'id': 'spk_1', 'name': 'Alice', 'color': '#5b9bd5'}],
        'entities': {},
        'mentions': {},
        'segments': [
            {
                'id': 'seg_1',
                'start': 0.0,
                'end': 4.2,
                'speakerId': 'spk_1',
                'words': [
                    {
                        'id': 'wrd_1',
                        'start': 0.0,
                        'end': 0.3,
                        'word': 'Hi',
                        'score': 1.0,
                        'speakerId': 'spk_1',
                    }
                ],
            }
        ],
    }


def content_with_entity():
    """A transcript whose single mention is linked to a single entity."""
    content = valid_content()
    content['mentions']['men_1'] = {'label': 'PER', 'entityId': 'ent_1'}
    content['entities'] = {
        'ent_1': {
            'name': 'Angela Merkel',
            'type': 'PER',
            'aliases': ['Merkel'],
            'wikidataId': 'Q567',
        }
    }
    content['segments'][0]['words'][0]['mentionId'] = 'men_1'
    return content


def test_accepts_valid():
    validate_mmt_content(valid_content())  # does not raise


def test_language_defaults_to_none_when_absent():
    transcript = validate_mmt_content(valid_content())
    assert transcript.language is None


def test_accepts_a_language():
    content = valid_content()
    content['language'] = 'de'
    transcript = validate_mmt_content(content)
    assert transcript.language == 'de'


def test_accepts_an_explicit_null_language():
    content = valid_content()
    content['language'] = None
    transcript = validate_mmt_content(content)
    assert transcript.language is None


def test_accepts_null_speaker_refs():
    content = valid_content()
    content['speakers'] = []
    content['segments'][0]['speakerId'] = None
    content['segments'][0]['words'][0]['speakerId'] = None
    validate_mmt_content(content)  # does not raise


def test_accepts_word_pointing_at_mention():
    content = valid_content()
    content['mentions']['men_1'] = {'label': 'PER'}
    content['segments'][0]['words'][0]['mentionId'] = 'men_1'
    validate_mmt_content(content)  # does not raise


def test_accepts_all_mention_labels():
    for label in ('PER', 'ORG', 'DATE', 'LOC'):
        content = valid_content()
        content['mentions']['men_1'] = {'label': label}
        content['segments'][0]['words'][0]['mentionId'] = 'men_1'
        validate_mmt_content(content)  # does not raise


def test_mention_score_defaults_to_one():
    content = valid_content()
    content['mentions']['men_1'] = {'label': 'PER'}
    content['segments'][0]['words'][0]['mentionId'] = 'men_1'
    transcript = validate_mmt_content(content)
    assert transcript.mentions['men_1'].score == 1.0


def test_accepts_mention_score():
    content = valid_content()
    content['mentions']['men_1'] = {'label': 'PER', 'score': 0.73}
    content['segments'][0]['words'][0]['mentionId'] = 'men_1'
    transcript = validate_mmt_content(content)
    assert transcript.mentions['men_1'].score == 0.73


def test_accepts_boundary_mention_scores():
    for score in (0.0, 1.0):
        content = valid_content()
        content['mentions']['men_1'] = {'label': 'PER', 'score': score}
        content['segments'][0]['words'][0]['mentionId'] = 'men_1'
        validate_mmt_content(content)  # does not raise


def test_rejects_orphaned_mention():
    # Every mention must be referenced by at least one word.
    content = valid_content()
    content['mentions']['men_1'] = {'label': 'PER'}
    with pytest.raises(ValidationError, match='orphaned mention'):
        validate_mmt_content(content)


def test_rejects_out_of_range_mention_score():
    for score in (-0.1, 1.1):
        content = valid_content()
        content['mentions']['men_1'] = {'label': 'PER', 'score': score}
        with pytest.raises(ValidationError):
            validate_mmt_content(content)


def test_rejects_non_float_mention_score():
    content = valid_content()
    content['mentions']['men_1'] = {'label': 'PER', 'score': 'high'}
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_unknown_mention_label():
    content = valid_content()
    content['mentions']['men_1'] = {'label': 'MISC'}
    content['segments'][0]['words'][0]['mentionId'] = 'men_1'
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_dangling_mention_id():
    content = valid_content()
    content['segments'][0]['words'][0]['mentionId'] = 'men_ghost'
    with pytest.raises(ValidationError, match='unknown mentionId'):
        validate_mmt_content(content)


def test_rejects_empty_mention_id():
    # Mention keys are ids like every other id: non-empty.
    content = valid_content()
    content['mentions'][''] = {'label': 'PER'}
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_mention_id_colliding_with_word_id():
    # Mention keys share the document-wide id namespace.
    content = valid_content()
    content['mentions']['wrd_1'] = {'label': 'PER'}
    with pytest.raises(ValidationError, match='duplicate id'):
        validate_mmt_content(content)


def test_rejects_unknown_word_key():
    content = valid_content()
    content['segments'][0]['words'][0]['ner_entity'] = 'PER'
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_non_dict():
    with pytest.raises(ValidationError):
        validate_mmt_content([])


def test_rejects_wrong_format():
    content = valid_content()
    content['format'] = 'whisper'
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_wrong_version():
    content = valid_content()
    content['version'] = 2
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_unknown_key():
    content = valid_content()
    content['segments'][0]['foo'] = 1
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_empty_segments():
    content = valid_content()
    content['segments'] = []
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_empty_words():
    content = valid_content()
    content['segments'][0]['words'] = []
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_bad_color():
    content = valid_content()
    content['speakers'][0]['color'] = 'blue'
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_dangling_segment_speaker_id():
    content = valid_content()
    content['segments'][0]['speakerId'] = 'spk_ghost'
    with pytest.raises(ValidationError, match='unknown speakerId'):
        validate_mmt_content(content)


def test_rejects_dangling_word_speaker_id():
    content = valid_content()
    content['segments'][0]['words'][0]['speakerId'] = 'spk_ghost'
    with pytest.raises(ValidationError, match='unknown speakerId'):
        validate_mmt_content(content)


def test_rejects_duplicate_speaker_id():
    content = valid_content()
    content['speakers'].append({'id': 'spk_1', 'name': 'Bob', 'color': '#70ad47'})
    with pytest.raises(ValidationError, match='duplicate id'):
        validate_mmt_content(content)


def test_rejects_duplicate_word_id_across_segments():
    content = valid_content()
    second = {
        'id': 'seg_2',
        'start': 5.0,
        'end': 6.0,
        'speakerId': 'spk_1',
        'words': [
            {
                'id': 'wrd_1',  # duplicate of the first segment's word id
                'start': 5.0,
                'end': 5.3,
                'word': 'Hi',
                'score': 1.0,
                'speakerId': 'spk_1',
            }
        ],
    }
    content['segments'].append(second)
    with pytest.raises(ValidationError, match='duplicate id'):
        validate_mmt_content(content)


def test_rejects_segment_start_after_end():
    content = valid_content()
    content['segments'][0]['start'] = 9.0
    with pytest.raises(ValidationError, match='start after end'):
        validate_mmt_content(content)


def test_rejects_word_start_after_end():
    content = valid_content()
    content['segments'][0]['words'][0]['start'] = 9.0
    with pytest.raises(ValidationError, match='start after end'):
        validate_mmt_content(content)


def test_accepts_boundary_word_scores():
    for score in (0.0, 1.0):
        content = valid_content()
        content['segments'][0]['words'][0]['score'] = score
        validate_mmt_content(content)  # does not raise


def test_rejects_out_of_range_word_score():
    for score in (-0.1, 1.1):
        content = valid_content()
        content['segments'][0]['words'][0]['score'] = score
        with pytest.raises(ValidationError):
            validate_mmt_content(content)


def test_rejects_content_without_entities():
    # The map is required, like speakers and segments. Content stored before
    # the field existed does not validate and has to be normalized first.
    content = valid_content()
    del content['entities']
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_mention_entity_id_defaults_to_none():
    # An unlinked mention may leave the key out, as it may leave out score.
    content = valid_content()
    content['mentions']['men_1'] = {'label': 'PER'}
    content['segments'][0]['words'][0]['mentionId'] = 'men_1'
    transcript = validate_mmt_content(content)
    assert transcript.mentions['men_1'].entityId is None


def test_accepts_a_register():
    validate_mmt_content(content_with_entity())  # does not raise


def test_entity_aliases_and_wikidata_id_are_optional():
    content = content_with_entity()
    content['entities']['ent_1'] = {'name': 'Angela Merkel', 'type': 'PER'}
    entity = validate_mmt_content(content).entities['ent_1']
    assert entity.aliases == []
    assert entity.wikidataId is None


def test_accepts_all_entity_types():
    for entity_type in ('PER', 'ORG', 'LOC'):
        content = content_with_entity()
        content['entities']['ent_1']['type'] = entity_type
        content['mentions']['men_1']['label'] = entity_type
        validate_mmt_content(content)  # does not raise


def test_rejects_date_entity_type():
    # A date has no identity, so no entity carries that type.
    content = content_with_entity()
    content['entities']['ent_1']['type'] = 'DATE'
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_accepts_a_label_differing_from_the_entity_type():
    # The label is the NER pass's claim, the type is the user's decision; the
    # validator does not force them to agree.
    content = content_with_entity()
    content['mentions']['men_1']['label'] = 'ORG'
    validate_mmt_content(content)  # does not raise


def test_rejects_dangling_entity_id():
    content = content_with_entity()
    content['mentions']['men_1']['entityId'] = 'ent_ghost'
    with pytest.raises(ValidationError, match='unknown entityId'):
        validate_mmt_content(content)


def test_rejects_orphaned_entity():
    # Every entity must be referenced by at least one mention.
    content = content_with_entity()
    content['mentions']['men_1']['entityId'] = None
    with pytest.raises(ValidationError, match='orphaned entity'):
        validate_mmt_content(content)


def test_rejects_empty_entity_id():
    content = content_with_entity()
    content['entities'][''] = {'name': 'Merkel', 'type': 'PER'}
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_entity_id_colliding_with_mention_id():
    # Entity keys share the document-wide id namespace.
    content = content_with_entity()
    content['entities']['men_1'] = content['entities'].pop('ent_1')
    content['mentions']['men_1']['entityId'] = 'men_1'
    with pytest.raises(ValidationError, match='duplicate id'):
        validate_mmt_content(content)


def test_rejects_entity_id_colliding_with_speaker_id():
    content = content_with_entity()
    content['entities']['spk_1'] = content['entities'].pop('ent_1')
    content['mentions']['men_1']['entityId'] = 'spk_1'
    with pytest.raises(ValidationError, match='duplicate id'):
        validate_mmt_content(content)


def test_rejects_empty_entity_name():
    content = content_with_entity()
    content['entities']['ent_1']['name'] = ''
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_empty_alias():
    content = content_with_entity()
    content['entities']['ent_1']['aliases'] = ['']
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_unknown_entity_key():
    content = content_with_entity()
    content['entities']['ent_1']['note'] = 'chancellor'
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_accepts_a_wikidata_id():
    content = content_with_entity()
    content['entities']['ent_1']['wikidataId'] = 'Q567'
    entity = validate_mmt_content(content).entities['ent_1']
    assert entity.wikidataId == 'Q567'


def test_accepts_a_null_wikidata_id():
    content = content_with_entity()
    content['entities']['ent_1']['wikidataId'] = None
    entity = validate_mmt_content(content).entities['ent_1']
    assert entity.wikidataId is None


def test_rejects_malformed_wikidata_ids():
    # Q0 and a leading zero are not Wikidata identifiers, the prefix is
    # required, and the pattern is anchored so a whole label is rejected.
    for wikidata_id in ('Q0', 'Q0567', '567', 'Q567x', 'Q567 (Angela Merkel)'):
        content = content_with_entity()
        content['entities']['ent_1']['wikidataId'] = wikidata_id
        with pytest.raises(ValidationError):
            validate_mmt_content(content)


def test_rejects_a_segment_text_key():
    # The format has no segment-level text: it duplicates the words and would
    # go stale when the words are edited.
    content = valid_content()
    content['segments'][0]['text'] = 'Hi'
    with pytest.raises(ValidationError, match='Extra inputs are not permitted'):
        validate_mmt_content(content)
