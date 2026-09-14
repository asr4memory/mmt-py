"""Numbers derived from mmt-transcript content, described in
specs/2026-09-14-transcript-statistics.md.
"""


def derive_statistics(content) -> dict:
    """Numbers derived from mmt-transcript content, for display."""
    if not isinstance(content, dict):
        content = {}

    segments = content.get('segments')

    return {
        'language': content.get('language'),
        'model': content.get('model'),
        'speaker_count': _count(content.get('speakers')),
        'segment_count': _count(segments),
        'word_count': _word_count(segments),
        'mention_count': _count(content.get('mentions')),
        'entity_count': _count(content.get('entities')),
        'redaction_count': _count(content.get('redactions')),
    }


def _count(collection):
    """The number of entries, or None when the key is absent or holds
    something other than a list or a map."""
    if isinstance(collection, (list, dict)):
        return len(collection)
    return None


def _word_count(segments):
    if not isinstance(segments, list):
        return None

    total = 0
    for segment in segments:
        words = segment.get('words') if isinstance(segment, dict) else None
        if isinstance(words, list):
            total += len(words)
    return total
