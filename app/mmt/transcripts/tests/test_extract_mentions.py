from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.normalize import extract_mentions


def content_with_words(words, *, segments=None):
    """An mmt-transcript whose single segment holds the given words, or the
    given list of word-lists as separate segments."""
    word_lists = segments if segments is not None else [words]
    return {
        'format': 'mmt-transcript',
        'version': 1,
        'speakers': [],
        'mentions': {},
        'segments': [
            {
                'id': f'seg_{i}',
                'start': 0.0,
                'end': 1.0,
                'text': 'x',
                'speakerId': None,
                'words': word_list,
            }
            for i, word_list in enumerate(word_lists)
        ],
    }


def word(id, **extra):
    return {'id': id, 'word': 'x', 'start': 0.0, 'end': 0.5, 'score': 1.0, **extra}


def test_single_word_entity_becomes_one_mention():
    content = extract_mentions(
        content_with_words([word('wrd_1', ner_entity='PER'), word('wrd_2')])
    )
    assert len(content['mentions']) == 1
    [(mention_id, mention)] = content['mentions'].items()
    assert mention['label'] == 'PER'
    words = content['segments'][0]['words']
    assert words[0]['mentionId'] == mention_id
    assert words[1]['mentionId'] is None


def test_multi_word_entity_shares_one_mention():
    content = extract_mentions(
        content_with_words(
            [
                word('wrd_1', ner_entity='LOC', word_group_index=0),
                word('wrd_2', ner_entity='LOC', word_group_index=0),
            ]
        )
    )
    assert len(content['mentions']) == 1
    words = content['segments'][0]['words']
    assert words[0]['mentionId'] == words[1]['mentionId']
    assert words[0]['mentionId'] in content['mentions']


def test_same_group_index_in_different_segments_is_distinct():
    # word_group_index is segment-scoped, so index 0 in two segments is two
    # different entities.
    content = extract_mentions(
        content_with_words(
            None,
            segments=[
                [
                    word('wrd_1', ner_entity='ORG', word_group_index=0),
                    word('wrd_2', ner_entity='ORG', word_group_index=0),
                ],
                [
                    word('wrd_3', ner_entity='PER', word_group_index=0),
                    word('wrd_4', ner_entity='PER', word_group_index=0),
                ],
            ],
        )
    )
    assert len(content['mentions']) == 2
    first = content['segments'][0]['words'][0]['mentionId']
    second = content['segments'][1]['words'][0]['mentionId']
    assert first != second


def test_drops_flat_ner_fields_and_validates():
    content = extract_mentions(
        content_with_words(
            [word('wrd_1', ner_entity='PER', word_group_index=0), word('wrd_2')]
        )
    )
    for w in content['segments'][0]['words']:
        assert 'ner_entity' not in w
        assert 'word_group_index' not in w
    validate_mmt_content(content)  # does not raise


def test_no_entities_yields_no_mentions():
    content = extract_mentions(content_with_words([word('wrd_1'), word('wrd_2')]))
    assert content['mentions'] == {}
    assert all(
        w['mentionId'] is None for w in content['segments'][0]['words']
    )
