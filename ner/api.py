import tomllib
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from words import entities_to_word_indices, join_words, resolve_overlaps
from model import ENTITY_LABELS, get_model

VERSION = tomllib.loads(
    (Path(__file__).parent / "pyproject.toml").read_text()
)["project"]["version"]

# The gliner2 library's own default. Entities with a lower confidence are
# discarded by the model and are not part of the response.
THRESHOLD = 0.5

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
* Each batch is sent to the model as one string, whatever its length.
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

Entities must reach a confidence of {THRESHOLD} to be returned. The threshold
is applied by the model itself: entities below it are never proposed, so they
cannot be recovered from the response at any score.

### Recognized labels

| Label | Meaning |
| --- | --- |
{LABEL_TABLE}
"""

EXAMPLE_REQUEST = {
    "batches": [
        ["Angela", "Merkel", "besuchte", "Berlin."],
        ["Das", "war", "2019."],
    ],
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


class HealthResponse(BaseModel):
    """Liveness of the service."""

    status: str = Field(description="Always `ok`.", examples=["ok"])
    version: str = Field(description="Version of the service.", examples=[VERSION])


@app.get(
    "/health",
    summary="Check that the service is up",
    description="Returns as soon as the process serves requests. The model is "
    "loaded on the first call to `/extract`, not here, so a successful "
    "response does not mean the model is in memory.",
    response_description="The service is up.",
)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=VERSION)


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
        422: {
            "description": "`batches` is missing or is not a list of word "
            "lists."
        },
    },
)
def extract(request: ExtractRequest) -> ExtractResponse:
    model, schema = get_model()
    results = []
    for batch in request.batches:
        if not batch:
            results.append([])
            continue
        text, offsets = join_words(batch)
        raw = model.extract(
            text,
            schema,
            threshold=THRESHOLD,
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
        results.append(resolve_overlaps(entities_to_word_indices(entities, offsets)))
    return ExtractResponse(results=results)
