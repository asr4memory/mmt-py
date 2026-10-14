import json
from pathlib import Path

import pytest

from mmt.transcripts.entity_linking import (
    matching_entity,
    mention_surfaces,
    normalized_surface,
)

CASES = json.loads(
    (Path(__file__).parent / 'data' / 'normalization_cases.json').read_text(
        encoding='utf-8'
    )
)


@pytest.mark.parametrize('case', CASES, ids=[repr(case['input']) for case in CASES])
def test_normalized_surface(case):
    assert normalized_surface(case['input']) == case['expected']


def word(word_id, text, mention_id=None):
    return {'id': word_id, 'word': text, 'mentionId': mention_id}


def test_mention_surfaces_joins_the_words_of_a_mention_in_order():
    content = {
        'segments': [
            {
                'words': [
                    word('w1', 'Angela', 'men_1'),
                    word('w2', 'Merkel', 'men_1'),
                    word('w3', 'and', None),
                    word('w4', 'Kohl', 'men_2'),
                ]
            }
        ]
    }
    assert mention_surfaces(content) == {'men_1': 'Angela Merkel', 'men_2': 'Kohl'}


def test_mention_surfaces_joins_a_mention_across_a_segment_boundary():
    content = {
        'segments': [
            {'words': [word('w1', 'Bundesrepublik', 'men_1')]},
            {'words': [word('w2', 'Deutschland', 'men_1'), word('w3', 'heute')]},
        ]
    }
    assert mention_surfaces(content) == {'men_1': 'Bundesrepublik Deutschland'}


ENTITIES = {
    'ent_1': {
        'name': 'Angela Merkel',
        'type': 'PER',
        'aliases': ['Merkel'],
        'wikidataId': 'Q567',
    },
    'ent_2': {'name': 'Berlin', 'type': 'LOC', 'aliases': [], 'wikidataId': None},
}


def test_matching_entity_matches_the_name():
    assert matching_entity('Angela Merkel', 'PER', ENTITIES) == 'ent_1'


def test_matching_entity_matches_an_alias():
    assert matching_entity('Merkel', 'PER', ENTITIES) == 'ent_1'


def test_matching_entity_ignores_case_and_edge_punctuation():
    assert matching_entity('„MERKEL“,', 'PER', ENTITIES) == 'ent_1'


def test_matching_entity_requires_the_same_type():
    assert matching_entity('Berlin', 'ORG', ENTITIES) is None
