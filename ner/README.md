# NER Service

Named entity recognition microservice based on GLiNER2.

The service is format-agnostic: it knows nothing about transcripts. `POST
/extract` takes word batches and returns entity spans as half-open
`[start, end)` word-index ranges, one span list per batch:

```json
// request
{"batches": [
  ["Angela", "Merkel", "besuchte", "Berlin."],
  ["Das", "war", "2019."]
]}

// response
{"results": [
  [{"start": 0, "end": 2, "label": "PER", "score": 0.93},
   {"start": 3, "end": 4, "label": "LOC", "score": 0.88}],
  [{"start": 2, "end": 3, "label": "DATE", "score": 0.91}]
]}
```

`results` is parallel to `batches`. Spans within one batch never overlap;
the service resolves overlaps itself (highest score wins).

## Running the service locally

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

### Start the server

```
uv run uvicorn api:app --reload
```

`uv run` executes the command inside the project's virtual environment, so the
environment does not have to be activated manually. `--reload` restarts the
server whenever a source file is changed, which is useful during development and
should not be used in production.

The server listens on http://localhost:8000.

The model weights (about 1 GB) are not part of the repository. They are
downloaded from Hugging Face when the first request arrives and are cached
afterwards, which is why the first request takes considerably longer than the
following ones. The server itself starts immediately.

### Send a request

Open http://localhost:8000/docs in a browser. This page is the Swagger UI. It
documents every endpoint and lets requests be sent from the browser: select
`POST /extract`, click *Try it out*, then *Execute*. The request body is already
filled in with an example, which can be edited before sending.

The same request from the command line:

```
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"batches": [["Angela", "Merkel", "besuchte", "Berlin."]]}'
```

A second, more compact rendering of the documentation is available at
http://localhost:8000/redoc. Both pages are generated from the OpenAPI schema at
http://localhost:8000/openapi.json, which is what other programs read to
generate a client for this service.

### Run the tests

```
uv run pytest
```

The tests replace the model with a stub, so they neither download the weights nor
run the model. They finish within seconds.
