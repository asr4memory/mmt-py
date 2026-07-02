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

## Development

Run the API locally:

```
uv run uvicorn api:app --reload
```

Once the server is running, open http://localhost:8000/docs in your browser to access the interactive API documentation.

Run the tests:

```
uv run pytest
```
