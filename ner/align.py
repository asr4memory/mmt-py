"""Alignment between word lists and character-span entities.

The model sees each batch as one string (words joined with single spaces).
All character-level bookkeeping stays in this module; only discrete word
indices cross the service boundary.
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


def to_word_spans(
    entities: list[dict], offsets: list[tuple[int, int]]
) -> list[dict]:
    """Map char-span entities onto non-overlapping word-index spans.

    Each entity is ``{"label", "start", "end", "score"}`` with half-open
    character offsets into the joined text. Any character overlap with a
    word claims the whole word. Overlapping word spans are resolved by
    score (highest wins, earlier span on ties). Returns
    ``{"start", "end", "label", "score"}`` spans with half-open word
    indices, sorted by start.
    """
    candidates = []
    for entity in entities:
        words = [
            index
            for index, (word_start, word_end) in enumerate(offsets)
            if word_start < entity["end"] and entity["start"] < word_end
        ]
        if not words:
            continue
        candidates.append(
            {
                "start": words[0],
                "end": words[-1] + 1,
                "label": entity["label"],
                "score": entity["score"],
            }
        )

    candidates.sort(key=lambda span: (-span["score"], span["start"]))
    claimed = set()
    accepted = []
    for span in candidates:
        indices = range(span["start"], span["end"])
        if claimed.isdisjoint(indices):
            claimed.update(indices)
            accepted.append(span)

    accepted.sort(key=lambda span: span["start"])
    return accepted
