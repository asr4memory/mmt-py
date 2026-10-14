"""Normalisation and matching of mention surfaces against the entity register.

The functions work on raw content dicts, because the NER task applies them to
content it is still mutating, before validation. entity_matching.ts implements
the same normalisation; tests/data/normalization_cases.json holds the cases
both implementations are tested against.
"""

import re
import unicodedata

_WHITESPACE = re.compile(r'\s+')


def _is_punctuation_or_symbol(character: str) -> bool:
    """Whether the character's Unicode category is punctuation (P*) or symbol (S*)."""
    return unicodedata.category(character)[0] in 'PS'


def _strip_punctuation_and_symbols(text: str) -> str:
    """Remove punctuation and symbols from the start and the end of the text."""
    # entity_matching.ts uses a regular expression with \p{P} and \p{S}. The
    # re module does not support Unicode categories, so this walks the text.
    # Index of the first character to keep.
    start = 0
    while start < len(text) and _is_punctuation_or_symbol(text[start]):
        start += 1

    # Index after the last character to keep. It does not go below start, so
    # a text of only punctuation and symbols becomes empty.
    end = len(text)
    while end > start and _is_punctuation_or_symbol(text[end - 1]):
        end -= 1

    return text[start:end]


def normalized_surface(text: str) -> str:
    """The form of a name or surface text that matching compares."""
    text = unicodedata.normalize('NFKC', text)
    text = _WHITESPACE.sub(' ', text).strip()
    text = _strip_punctuation_and_symbols(text)
    # Stripping "„ Merkel “" leaves spaces at both ends.
    text = text.strip()
    # str.lower rather than str.casefold, which maps ß to ss where
    # JavaScript's toLowerCase does not.
    return text.lower()


def mention_surfaces(content: dict) -> dict[str, str]:
    """Surface text of every mention: its words across the whole document, in order."""
    words_by_mention = {}
    for segment in content['segments']:
        for word in segment['words']:
            mention_id = word.get('mentionId')
            if mention_id is not None:
                words_by_mention.setdefault(mention_id, []).append(word['word'])
    return {
        mention_id: ' '.join(words)
        for mention_id, words in words_by_mention.items()
    }


def matching_entity(surface: str, type: str, entities: dict) -> str | None:
    """Identifier of the entity that rule A matches, or None.

    Rule A: the entity's type equals the given type, and its normalised name
    or one of its normalised aliases equals the normalised surface. The
    uniqueness of names and aliases in the register makes the result unique."""
    normalized = normalized_surface(surface)
    for entity_id, entity in entities.items():
        if entity['type'] != type:
            continue
        names = [entity['name'], *entity['aliases']]
        if any(normalized_surface(name) == normalized for name in names):
            return entity_id
    return None
