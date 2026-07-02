"""Alignment between word lists and character-span entities.

The model sees each window of a batch as one string (words joined with
single spaces). All character-level bookkeeping stays in this module; only
discrete word indices cross the service boundary.

Long batches are split into overlapping windows because the encoder tops out
at ~512 subword tokens (shared with the schema's label descriptions; German
runs ~1.5 subtokens per word) and GLiNER2 does no windowing of its own —
``max_len`` silently drops everything beyond the limit.
"""

WINDOW = 180
OVERLAP = 40


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


def windows(
    count: int, window: int = WINDOW, overlap: int = OVERLAP
) -> list[tuple[int, int]]:
    """Half-open word ranges covering ``[0, count)``.

    Consecutive windows share exactly ``overlap`` words, so any entity
    shorter than the overlap lies fully interior to at least one window.
    The final window may be shorter than ``window`` but is always longer
    than ``overlap``.
    """
    if count <= window:
        return [(0, count)]
    stride = window - overlap
    result = []
    start = 0
    while start + window < count:
        result.append((start, start + window))
        start += stride
    result.append((start, count))
    return result


def word_candidates(
    entities: list[dict], offsets: list[tuple[int, int]]
) -> list[dict]:
    """Map char-span entities onto word-index span candidates.

    Each entity is ``{"label", "start", "end", "score"}`` with half-open
    character offsets into the joined text. Any character overlap with a
    word claims the whole word. Candidates may overlap each other; resolve
    with ``merge_windows`` (or ``to_word_spans`` for a single unwindowed
    batch).
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
    return candidates


def merge_windows(
    candidates_per_window: list[tuple[tuple[int, int], list[dict]]],
    count: int,
) -> list[dict]:
    """Merge per-window candidates into non-overlapping batch spans.

    Takes ``((window_start, window_end), candidates)`` pairs, with candidate
    spans in window-local word indices. Shifts candidates into batch
    coordinates and discards any candidate touching a *cut* edge of its
    window (batch boundaries are real text edges and don't discard): a cut
    can slice an entity, and the truncated reading must not outscore the
    neighboring window's full detection — which the overlap guarantees
    exists. Duplicates detected by two overlapping windows collapse in the
    claim set (higher score wins).
    """
    merged = []
    for (window_start, window_end), candidates in candidates_per_window:
        length = window_end - window_start
        for span in candidates:
            if window_start > 0 and span["start"] == 0:
                continue
            if window_end < count and span["end"] == length:
                continue
            merged.append(
                {
                    **span,
                    "start": span["start"] + window_start,
                    "end": span["end"] + window_start,
                }
            )
    return _resolve(merged)


def to_word_spans(
    entities: list[dict], offsets: list[tuple[int, int]]
) -> list[dict]:
    """Map char-span entities of one unwindowed batch onto non-overlapping
    word-index spans: ``word_candidates`` resolved by score. Returns
    ``{"start", "end", "label", "score"}`` spans with half-open word
    indices, sorted by start.
    """
    return _resolve(word_candidates(entities, offsets))


def _resolve(candidates: list[dict]) -> list[dict]:
    """Resolve overlapping candidates: highest score wins, earlier span on
    ties. Returns accepted spans sorted by start."""
    ranked = sorted(candidates, key=lambda span: (-span["score"], span["start"]))
    claimed = set()
    accepted = []
    for span in ranked:
        indices = range(span["start"], span["end"])
        if claimed.isdisjoint(indices):
            claimed.update(indices)
            accepted.append(span)

    accepted.sort(key=lambda span: span["start"])
    return accepted
