# NER Service

Named entity recognition microservice based on GLiNER2.

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
