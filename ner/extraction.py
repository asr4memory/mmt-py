from model import get_model
from windowing import OVERLAP, WINDOW, merge_windows, windows
from words import entities_to_word_indices, join_words

# Belongs to WINDOW in windowing.py: the two are tuned together, see the comment
# there. 0.3 goes with a 180-word window, 0.4 with a 72-word window.
DEFAULT_THRESHOLD = 0.3


def extract(
    batches: list[list[str]],
    threshold: float = DEFAULT_THRESHOLD,
    window: int | None = WINDOW,
    overlap: int = OVERLAP,
) -> list[list[dict]]:
    """Return one list of non-overlapping entity spans per batch."""
    model, schema = get_model()
    return [
        _extract_batch(model, schema, batch, threshold, window, overlap)
        for batch in batches
    ]


def _extract_batch(model, schema, batch, threshold, window, overlap) -> list[dict]:
    if not batch:
        return []
    if window is None:
        window_ranges = [(0, len(batch))]
    else:
        window_ranges = windows(len(batch), window, overlap)
    candidates_per_window = []
    for window_start, window_end in window_ranges:
        text, offsets = join_words(batch[window_start:window_end])
        raw = model.extract(
            text,
            schema,
            threshold=threshold,
            include_spans=True,
            include_confidence=True,
        )
        entities = [
            {
                "label": label,
                "start": entity["start"],
                "end": entity["end"],
                "score": entity["confidence"],
            }
            for label, found in raw["entities"].items()
            for entity in found
        ]
        candidates_per_window.append(
            (
                (window_start, window_end),
                entities_to_word_indices(entities, offsets),
            )
        )
    return merge_windows(candidates_per_window, len(batch))
