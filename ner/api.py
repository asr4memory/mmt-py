from fastapi import FastAPI
from pydantic import BaseModel

from align import join_words, to_word_spans
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
        text, offsets = join_words(batch)
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
        results.append(to_word_spans(entities, offsets))
    return ExtractResponse(results=results)
