from fastapi import FastAPI
from pydantic import BaseModel

from align import join_words, merge_windows, windows, word_candidates
from model import get_model

app = FastAPI()


class ExtractRequest(BaseModel):
    batches: list[list[str]]


class EntitySpan(BaseModel):
    """Half-open [start, end) word-index span within one batch."""

    start: int
    end: int
    label: str
    score: float


class ExtractResponse(BaseModel):
    """One span list per batch, parallel to the request's batches."""

    results: list[list[EntitySpan]]


@app.post("/extract")
def extract(request: ExtractRequest) -> ExtractResponse:
    model, schema = get_model()
    results = []
    for batch in request.batches:
        if not batch:
            results.append([])
            continue
        candidates_per_window = []
        for window_start, window_end in windows(len(batch)):
            text, offsets = join_words(batch[window_start:window_end])
            raw = model.extract(
                text, schema, include_spans=True, include_confidence=True
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
                ((window_start, window_end), word_candidates(entities, offsets))
            )
        results.append(merge_windows(candidates_per_window, len(batch)))
    return ExtractResponse(results=results)
