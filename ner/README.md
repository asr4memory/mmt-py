# NER Service

Named entity recognition worker based on GLiNER2.

The service is a Celery worker that consumes the `ner` queue with a
concurrency of 1. The app sends the task `ner.extract` by name; the worker
runs it and returns the result to the app through the Celery link callback.

The service is format-agnostic: it knows nothing about transcripts. The task
takes word batches and returns entity spans as half-open `[start, end)`
word-index ranges, one span list per batch:

```python
# argument
[
    ["Angela", "Merkel", "besuchte", "Berlin."],
    ["Das", "war", "2019."],
]

# return value
[
    [{"start": 0, "end": 2, "label": "PER", "score": 0.93},
     {"start": 3, "end": 4, "label": "LOC", "score": 0.88}],
    [{"start": 2, "end": 3, "label": "DATE", "score": 0.91}],
]
```

The return value is parallel to the batches. Spans within one batch do not
overlap: if the model detects overlapping entities, the span with the higher
score is kept and the other is discarded. An empty batch returns an empty span
list without calling the model.

The words of a batch are joined with single spaces into one string, which is
what the model receives. The model returns character ranges, which are
converted back into word indices: a word is part of a span if at least one of
its characters lies within the character range.

A batch longer than `WINDOW` words (in `windowing.py`) is split into windows
that share `OVERLAP` words, and the spans of all windows are merged afterwards.
The model's confidence in an entity decreases as the surrounding text grows, so
`WINDOW` and `DEFAULT_THRESHOLD` (in `extraction.py`) are tuned together.

The labels and their descriptions are in `ENTITY_LABELS` in `model.py`.

## Running the worker locally

### Prerequisites

The project uses [uv](https://docs.astral.sh/uv/) to manage its Python version
and its dependencies. Install it by following the
[official installation instructions](https://docs.astral.sh/uv/getting-started/installation/).

Nothing else has to be installed beforehand. uv downloads the required Python
version (see `requires-python` in `pyproject.toml`) and creates a virtual
environment in `.venv` on its own.

### Install the dependencies

From this directory (`ner/`):

```
uv sync
```

This reads `uv.lock` and installs the exact dependency versions the project was
locked to, among them PyTorch, which is several hundred megabytes. The first run
therefore takes a few minutes.

### Start the worker

The worker needs a Redis instance as broker and result backend:

```
CELERY_BROKER_URL=redis://localhost CELERY_RESULT_BACKEND=redis://localhost \
  uv run celery -A tasks worker -Q ner -n ner@%h --concurrency=1 -l INFO
```

The model weights (about 1 GB) are not part of the repository. They are
downloaded from Hugging Face when the first task runs and are cached
afterwards, which is why the first task takes considerably longer than the
following ones.

### Evaluate the extraction

`examples/evaluate.py` runs the extraction in-process on an example transcript
and compares the spans with a gold annotation:

```
uv run python examples/evaluate.py
```

### Run the tests

```
uv run pytest
```

The tests replace the model with a stub, so they neither download the weights nor
run the model. They finish within seconds.
