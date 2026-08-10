"""Mapping between word lists and character-span entities.

The model receives its input as one string (words joined with single
spaces). All character-level bookkeeping stays in this module; only
discrete word indices cross the service boundary.
"""


def join_words(words: list[str]) -> tuple[str, list[tuple[int, int]]]:
    """Join words with single spaces.

    Returns the joined text and each word's half-open ``[start, end)``
    character range within it.
    """
    offsets = []
    position = 0
    for word in words:
        offsets.append((position, position + len(word)))
        position += len(word) + 1
    return " ".join(words), offsets


def entities_to_word_indices(
    entities: list[dict], offsets: list[tuple[int, int]]
) -> list[dict]:
    """Map char-span entities onto word-index spans.

    Each entity is ``{"label", "start", "end", "score"}`` with half-open
    character offsets into the joined text. A word is part of a span if at
    least one of its characters lies within the entity's character range;
    an entity whose range covers no word yields no span. Spans are returned
    in the order of the entities they came from and are not resolved
    against each other: when entities overlap, their spans do too.
    """
    spans = []
    for entity in entities:
        words = [
            index
            for index, (word_start, word_end) in enumerate(offsets)
            if word_start < entity["end"] and entity["start"] < word_end
        ]
        if not words:
            continue
        spans.append(
            {
                "start": words[0],
                "end": words[-1] + 1,
                "label": entity["label"],
                "score": entity["score"],
            }
        )
    return spans


def resolve_overlaps(spans: list[dict]) -> list[dict]:
    """Resolve overlapping spans: the span with the higher score is kept and
    the other is discarded, the earlier span on ties. Returns the accepted
    spans sorted by start."""
    ranked = sorted(spans, key=lambda span: (-span["score"], span["start"]))
    claimed = set()
    accepted = []
    for span in ranked:
        indices = range(span["start"], span["end"])
        if claimed.isdisjoint(indices):
            claimed.update(indices)
            accepted.append(span)

    accepted.sort(key=lambda span: span["start"])
    return accepted
