import tomllib
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from align import join_words, merge_windows, windows, word_candidates
from model import ENTITY_LABELS, get_model

VERSION = tomllib.loads(
    (Path(__file__).parent / "pyproject.toml").read_text()
)["project"]["version"]

DESCRIPTION = """
Named entity recognition based on [GLiNER2](https://github.com/fastino-ai/GLiNER2).

The service is format-agnostic and makes no assumptions about the origin of
the text. It accepts **word batches** and returns **entity spans** as
half-open `[start, end)` word-index ranges into those batches.

* `results` is parallel to `batches`: one span list per batch, in the same
  order.
* Spans within a batch do not overlap. If the model detects overlapping
  entities, the service keeps the one with the higher score and discards the
  other.
* Batches of any length are accepted. Batches longer than the model's input
  limit are split into overlapping windows internally, so the caller does not
  have to split them.
"""

LABEL_TABLE = "\n".join(
    f"| `{label}` | {description} |" for label, description in ENTITY_LABELS.items()
)

EXTRACT_DESCRIPTION = f"""
Each batch is a list of words. The words of a batch are joined with single
spaces into one string, which is what the model receives. The model returns
character ranges, and the service converts them back into word indices: a word
is part of a span if at least one of its characters lies within the character
range.

An empty batch returns an empty span list. The model is not called for it.

### Recognized labels

| Label | Meaning |
| --- | --- |
{LABEL_TABLE}
"""

EXAMPLE_REQUEST = {
    "batches": [
        ["Angela", "Merkel", "besuchte", "Berlin."],
        ["Das", "war", "2019."],
    ]
}

EXAMPLE_RESPONSE = {
    "results": [
        [
            {"start": 0, "end": 2, "label": "PER", "score": 0.93},
            {"start": 3, "end": 4, "label": "LOC", "score": 0.88},
        ],
        [{"start": 2, "end": 3, "label": "DATE", "score": 0.91}],
    ]
}

app = FastAPI(
    title="NER Service",
    summary="Named entity recognition over word batches.",
    description=DESCRIPTION,
    version=VERSION,
)


class ExtractRequest(BaseModel):
    """Word batches to extract entities from."""

    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_REQUEST]})

    batches: list[list[str]] = Field(
        description="One list of words per batch. Each batch is processed "
        "independently of the others."
    )


class EntitySpan(BaseModel):
    """Half-open [start, end) word-index span within one batch."""

    start: int = Field(ge=0, description="Index of the span's first word.")
    end: int = Field(
        ge=0, description="Index one past the span's last word (exclusive)."
    )
    label: str = Field(
        description="Entity type. One of: " + ", ".join(ENTITY_LABELS),
        examples=["PER"],
    )
    score: float = Field(ge=0, le=1, description="Model confidence, 0 to 1.")


class ExtractResponse(BaseModel):
    """One span list per batch, parallel to the request's batches."""

    results: list[list[EntitySpan]] = Field(
        description="One span list per batch, in the order in which the "
        "batches were sent. Spans within a batch do not overlap and are "
        "sorted by their start index."
    )


@app.post(
    "/extract",
    summary="Extract entities from word batches",
    description=EXTRACT_DESCRIPTION,
    response_description="One list of non-overlapping entity spans per batch.",
    responses={
        200: {"content": {"application/json": {"example": EXAMPLE_RESPONSE}}},
        422: {"description": "`batches` is missing or is not a list of word lists."},
    },
)
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
