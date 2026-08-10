"""Windowing of long batches and merging of per-window candidates.

Long batches are split into overlapping windows because the model's confidence
in an entity decays as the surrounding text grows, not because of a length
limit. The encoder has no hard limit: mdeberta-v3 uses relative position
embeddings, and entities are still detected beyond 800 subtokens.

Windowing keeps the scores high enough to survive the extraction threshold.
Measured on a 566-word English interview, "Internet Society" scores 0.80 in a
72-word window, 0.32 in a 180-word window and 0.07 in a 360-word window, while
an unambiguous name such as "FCC" stays at 0.99 in all of them. Window size and
threshold are therefore coupled: a threshold tuned for one window size is wrong
for another. Both are measured together by examples/evaluate.py against a gold
annotation.
"""

# Measured with examples/evaluate.py on two transcripts, a 566-word English
# interview and a 461-word German panel introduction, as precision/recall/F1:
#
#   window 180, overlap 40, threshold 0.3  en 1.00/0.83/0.91   de 1.00/0.83/0.91
#   window 72, overlap 16, threshold 0.4   en 0.94/0.89/0.91   de 0.88/0.78/0.82
#
# The 180-word window is in use: equal to the 72-word window on English, better
# on German, and it produced no false positives on either transcript. The
# 72-word window finds more entities in English (recall 0.89) at the cost of
# precision, and is the alternative if a missed entity is worse than a wrong
# one.
#
# Treat the gap between these two as weak evidence. Both transcripts hold 18
# gold entities, so a single entity moves recall by about 0.06, and pseudonymi-
# zing three person names in the German transcript was enough to reverse which
# of the two settings won. What has held up across every run is only the ends
# of the range: windows of 360 words (about 2000 characters) are consistently
# worse, with recall at 0.72 or below, because the scores decay as described
# above.
#
# Changing WINDOW without changing DEFAULT_THRESHOLD in api.py (and the other
# way round) gives a worse result than either setting above.
WINDOW = 180
OVERLAP = 40


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


def _resolve(candidates: list[dict]) -> list[dict]:
    """Resolve overlapping candidates: the candidate with the higher score is
    kept and the other is discarded, the earlier span on ties. Returns the
    accepted spans sorted by start."""
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
