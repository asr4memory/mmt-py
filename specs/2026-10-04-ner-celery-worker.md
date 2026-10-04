# NER as a Celery worker

This is an executable spec. It is the authoritative record of the decisions for
running the NER service as a Celery worker instead of an HTTP API. An
implementing session works from this document and resolves ambiguity by
reading it.

## Motivation

`enrich_transcript` in [`transcripts/tasks.py`](../app/mmt/transcripts/tasks.py)
sends all word batches of a transcript to `POST /extract` and waits up to
15 minutes for the response. When two extractions run at the same time, they
share the 2 CPUs of the NER container, and each exceeds the timeout. The result
is lost and the user has to start the extraction again.

As a Celery worker with a concurrency of 1, the NER service takes the jobs from
a queue one after another. A waiting job keeps no connection open and cannot
time out. A job whose worker stops during inference stays in the broker and is
run again when the worker restarts. The NER service is changed and the ASR
service is not, so the two designs can be compared in operation.

## Non-goals

- **No change to the ASR service.**
- **No progress reporting.** The task does not call `update_state`.
- **No status shown to the user.** As before, a failed extraction is visible
  only in the logs.
- **No time limit on the NER task.**
- **No removal of the HTTP API.** `ner/api.py` and its tests stay in the
  repository, but the image no longer starts it.
- **No protection against a job that stops the worker every time**, for example
  by exceeding the memory limit. Such a job is delivered again indefinitely.

## Feature reference

### Message flow

1. The view calls `enrich_transcript.delay(transcript_id)` as before.
2. `enrich_transcript` creates a UUID `task_id` and sends the task by name,
   without importing NER code:
   `send_task('ner.extract', args=[batch_words], queue='ner', task_id=task_id, link=store_entities.s(transcript_id, content, task_id).set(queue='celery'))`.
   `content` is the deep copy of the transcript content from which the batches
   were built. The callback therefore applies the spans to the same words even
   if the transcript is edited while the job is waiting.
3. The NER worker runs `ner.extract` and returns `list[list[dict]]` with the
   keys `start`, `end`, `label` and `score`. This is the same structure as the
   `results` of the HTTP API.
4. Celery sends `store_entities(results, transcript_id, content, ner_task_id)`
   to the `celery` queue, and the app's worker runs it.

### Idempotency

`Transcript` gets the field
`ner_task_id = models.UUIDField(null=True, blank=True, unique=True, editable=False)`.
`store_entities` creates the NER transcript with
`Transcript.objects.get_or_create(ner_task_id=..., defaults=...)`. A second
delivery of the same job therefore does not create a second transcript.

### Worker configuration

[`ner/tasks.py`](../ner/tasks.py) defines `app = Celery('ner')` with:

| Setting | Value |
| --- | --- |
| `broker_url` | environment variable `CELERY_BROKER_URL` |
| `task_acks_late` | `True` |
| `task_reject_on_worker_lost` | `True` |
| `worker_prefetch_multiplier` | `1` |
| `task_ignore_result` | `True` |

Redis delivers an unacknowledged message again after `visibility_timeout`,
which stays at its default of 1 hour on both sides. A NER task must finish
within that time.

The image `CMD` is `celery -A tasks worker -Q ner -n ner@%h --concurrency=1 -l INFO`.
The health check is `celery -A tasks inspect ping -d ner@$HOSTNAME`.

## File layout

- `ner/extraction.py`: `extract(batches, threshold=DEFAULT_THRESHOLD, window=WINDOW, overlap=OVERLAP) -> list[list[dict]]`,
  moved out of the `/extract` route, which calls it.
- `ner/tasks.py`: the Celery app and `extract_entities(batches)`, registered as
  `ner.extract`.
- `ner/pyproject.toml`: adds `celery[redis]~=5.5`, the same version as the app.
- `app/mmt/transcripts/tasks.py`: `enrich_transcript` sends the task;
  `store_entities` is new. `NER_TIMEOUT` and `MMT_NER_API_URL` are removed.

## Slices

### Slice 1: Celery task in the NER service

- [ ] Move the extraction into `extraction.py`, add `tasks.py` and the
  dependency. The image still starts uvicorn.
  Done when: `test_api.py` passes unchanged, and a test calls
  `extract_entities` with the batches of `EXAMPLE_REQUEST` and receives one
  span list per batch.

### Slice 2: app uses the worker

The NER container is replaced before the app is deployed. Extractions that run
during the switch fail.

- [ ] Add `ner_task_id` with its migration and `store_entities`; change
  `enrich_transcript` to send the task. Convert the `enrich_transcript` tests in
  `test_tasks.py` to pytest style.
  Done when: tests show that `enrich_transcript` calls `send_task` with the
  batch words, the `ner` queue and a `store_entities` link; that
  `store_entities` creates the NER transcript with its mentions; that two calls
  with the same `ner_task_id` create one transcript; and that invalid spans
  raise `ValidationError` without creating a transcript.
- [ ] Switch the image `CMD` and the health check, and update
  `docker-compose.yml` (broker URL, `depends_on: redis`), `deploy/create-mmt-ner`
  (`--env CELERY_BROKER_URL`, no published port), `deploy/README.md` and
  `env.list` (no `NER_API_URL`).
  Done when: in the compose stack, two extractions started at the same time
  both create a NER transcript, and an extraction whose NER container is
  restarted during inference creates its transcript after the restart.
