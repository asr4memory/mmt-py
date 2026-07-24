import tomllib
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field, model_validator

from align import (
    OVERLAP,
    WINDOW,
    join_words,
    merge_windows,
    windows,
    word_candidates,
)
from model import ENTITY_LABELS, get_model

VERSION = tomllib.loads(
    (Path(__file__).parent / "pyproject.toml").read_text()
)["project"]["version"]

# Belongs to WINDOW in align.py: the two are tuned together, see the comment
# there. 0.3 goes with a 180-word window, 0.4 with a 72-word window.
DEFAULT_THRESHOLD = 0.3

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
* Batches of any length are accepted. Long batches are split into overlapping
  windows internally, so the caller does not have to split them. The window
  size is configurable per request, and the splitting can be switched off.
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

`threshold` is the minimum confidence an entity must reach. It is applied by
the model itself: entities below it are never proposed, so they cannot be
recovered from the response at any score. A lower value returns more entities
and more false positives.

`window` and `overlap` control how a batch is split before the model sees it.
A batch of at most `window` words is sent as one string. A longer batch is
split into windows of `window` words, where consecutive windows share
`overlap` words, and the spans of all windows are merged afterwards. Setting
`window` to `null` switches the splitting off: the whole batch is sent as one
string, however long it is.

The model's confidence in an entity decays as the surrounding text grows, so
`window` and `threshold` are coupled: a threshold tuned for one window size is
wrong for another. The defaults of {DEFAULT_THRESHOLD} and {WINDOW} are tuned
together. On a 566-word English interview and a 461-word German panel
introduction they reach a precision of 1.00 and a recall of 0.83 on both.
Raising the threshold trades recall for precision, lowering it does the
reverse.

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
    "threshold": DEFAULT_THRESHOLD,
    "window": WINDOW,
    "overlap": OVERLAP,
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
    threshold: float = Field(
        default=DEFAULT_THRESHOLD,
        ge=0,
        le=1,
        examples=[DEFAULT_THRESHOLD],
        description="Minimum confidence an entity must reach to be returned. "
        "Entities below this value are discarded by the model and are not "
        "part of the response at any score. Lower values return more entities "
        "and more false positives.",
    )
    window: int | None = Field(
        default=WINDOW,
        gt=0,
        examples=[WINDOW],
        description="Number of words per window. Batches longer than this are "
        "split into windows of this many words before the model sees them. "
        "`null` switches the splitting off and sends every batch as one "
        "string. This value is tuned together with `threshold`; changing one "
        "without the other gives worse results than either default.",
    )
    overlap: int = Field(
        default=OVERLAP,
        ge=0,
        examples=[OVERLAP],
        description="Number of words consecutive windows share. An entity "
        "shorter than this lies fully inside at least one window, which is "
        "what lets a window cut through an entity without losing it. Must be "
        "smaller than `window`. Ignored when `window` is `null`.",
    )

    @model_validator(mode="after")
    def check_overlap_smaller_than_window(self) -> "ExtractRequest":
        if self.window is not None and self.overlap >= self.window:
            raise ValueError("overlap must be smaller than window")
        return self


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
            "lists, or a parameter is outside its range: `threshold` outside "
            "0 to 1, `window` not positive, `overlap` negative or not smaller "
            "than `window`."
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
        if request.window is None:
            window_ranges = [(0, len(batch))]
        else:
            window_ranges = windows(len(batch), request.window, request.overlap)
        candidates_per_window = []
        for window_start, window_end in window_ranges:
            text, offsets = join_words(batch[window_start:window_end])
            raw = model.extract(
                text,
                schema,
                threshold=request.threshold,
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
                ((window_start, window_end), word_candidates(entities, offsets))
            )
        results.append(merge_windows(candidates_per_window, len(batch)))
    return ExtractResponse(results=results)
