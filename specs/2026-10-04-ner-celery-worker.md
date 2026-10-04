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

The design is a prototype. It also tests two Celery mechanisms that the ASR
service implements by hand: the status of a job and an automatic retry after a
failure.

## Non-goals

- **No change to the ASR service.**
- **No status in the user interface.** The status of an extraction is shown
  only in the Django admin.
- **No progress or running state.** The app does not read the state of a
  running task from the result backend. A job keeps the status `queued` until a
  callback writes its final status.
- **No resumption of a retried job.** A retry runs all batches again from the
  first one.
- **No time limit on the NER task.**
- **No protection against a job that stops the worker every time**, for example
  by exceeding the memory limit. Such a job is delivered again indefinitely.
  Automatic retry applies only to exceptions raised by the task.

## Feature reference

### Message flow

1. The view calls `enrich_transcript.delay(transcript_id)` as before.
2. `enrich_transcript` creates an `EntityExtractionJob` with status `queued`
   and sends the task by name, with the job's `task_id` as Celery task id and
   without importing NER code:
   `send_task('ner.extract', args=[batch_words], queue='ner', task_id=str(job.task_id), link=store_entities.s(job.pk, content).set(queue='celery'), link_error=mark_extraction_failed.si(job.pk).set(queue='celery'))`.
   `content` is the deep copy of the transcript content from which the batches
   were built. The callback therefore applies the spans to the same words even
   if the transcript is edited while the job is waiting.
3. The NER worker runs `ner.extract` and returns `list[list[dict]]` with the
   keys `start`, `end`, `label` and `score`. This is the same structure as the
   `results` of the former HTTP API.
4. On success, Celery sends `store_entities(results, job_id, content)` to the
   `celery` queue, and the app's worker runs it.
5. After the last retry has failed, Celery sends
   `mark_extraction_failed(job_id)` to the `celery` queue instead. A failed
   attempt that is followed by a retry does not call it.

### Job model

`EntityExtractionJob` in `transcripts/models.py`, modelled on
`TranscriptionJob`:

| Field | Definition |
| --- | --- |
| `transcript` | `ForeignKey(Transcript, on_delete=CASCADE, related_name='entity_extraction_jobs')`, the source transcript |
| `task_id` | `UUIDField(default=uuid.uuid4, unique=True, editable=False)`, the Celery task id |
| `status` | `CharField(max_length=20, choices=STATUS_CHOICES, default=QUEUED)` |
| `error` | `TextField(blank=True)` |
| `result_transcript` | `ForeignKey(Transcript, on_delete=SET_NULL, null=True, blank=True, related_name='+')`, the NER transcript |
| `created_at`, `updated_at` | as in `TranscriptionJob` |

The status values are `queued`, `succeeded` and `failed`, with the labels
"Queued", "Succeeded" and "Failed".

### Idempotency

`store_entities` locks the job with `select_for_update()` and returns without a
change if `result_transcript` is set. Otherwise it creates the NER transcript,
sets `result_transcript`, and sets the status to `succeeded`, in one
transaction. A second delivery of the same job therefore does not create a
second transcript.

`store_entities` does not retry. If the spans are invalid, it sets the status
to `failed`, stores `ValidationError: <message>` in `error`, and raises the
`ValidationError` again so that the failure is logged. No transcript is
created.

### Failure

`mark_extraction_failed(job_id)` is an immutable signature, so Celery passes it
no arguments of its own. It reads the exception from
`AsyncResult(str(job.task_id)).result` and stores it as
`<exception class name>: <message>` in `error`, and sets the status to
`failed`. It does not change a job whose status is already `succeeded`.

### Retry

`ner.extract` is declared with:

| Option | Value |
| --- | --- |
| `autoretry_for` | `(Exception,)` |
| `max_retries` | `3` |
| `retry_backoff` | `True` (at most 1, 2, 4 seconds; with jitter, each delay is a random value between 0 and that limit) |
| `retry_backoff_max` | `600` |
| `retry_jitter` | `True` |

A retry sends the job again with the same task id and the same `link` and
`link_error` signatures.

### Admin

`EntityExtractionJobAdmin` is read-only, like `TranscriptionJobAdmin`. The
list shows `transcript`, `status` and `created_at`, and filters by `status` and
`created_at`. The detail page shows all fields.

### Worker configuration

[`ner/tasks.py`](../ner/tasks.py) defines `app = Celery('ner')` with:

| Setting | Value |
| --- | --- |
| `broker_url` | environment variable `CELERY_BROKER_URL` |
| `task_acks_late` | `True` |
| `task_reject_on_worker_lost` | `True` |
| `worker_prefetch_multiplier` | `1` |
| `result_backend` | environment variable `CELERY_RESULT_BACKEND` |

Redis delivers an unacknowledged message again after `visibility_timeout`,
which stays at its default of 1 hour on both sides. A NER task must finish
within that time.

The app gets the setting `CELERY_RESULT_BACKEND` from the environment variable
of the same name, with the same value as in the NER service. If the variable is
not set, the app uses `CELERY_BROKER_URL`. Both use the existing Redis, and the
result backend can have the same URL as the broker. `result_expires` stays at
its default of 1 day; the durable status is in the database. The result backend
also stores the results of the app's own tasks, which expire in the same way.
The app reads the result backend only for the exception of a failed task.

The image `CMD` is `celery -A tasks worker -Q ner -n ner@%h --concurrency=1 -l INFO`.
The health check is `celery -A tasks inspect ping -d ner@$(hostname)`.

## File layout

- `ner/extraction.py`: `extract(batches, threshold=DEFAULT_THRESHOLD, window=WINDOW, overlap=OVERLAP) -> list[list[dict]]`,
  moved out of the `/extract` route.
- `ner/test_extraction.py`: the extraction tests of `test_api.py`, calling
  `extract()` directly.
- `ner/api.py` and `ner/test_api.py`: deleted.
- `ner/pyproject.toml`, `ner/Dockerfile`: `fastapi`, `uvicorn`, `httpx2` and
  `curl` are removed.
- `ner/examples/evaluate.py`: calls `extract()` in-process instead of
  `POST /extract`.
- `ner/README.md`: describes the Celery task instead of the HTTP API.
- `ner/tasks.py`: the Celery app and `extract_entities(batches)`,
  registered as `ner.extract`.
- `ner/pyproject.toml`: adds `celery[redis]~=5.5`, the same version as the app.
- `app/mmt/transcripts/models.py`: `EntityExtractionJob`.
- `app/mmt/transcripts/admin.py`: `EntityExtractionJobAdmin`.
- `app/mmt/transcripts/tasks.py`: `enrich_transcript` creates the job and sends
  the task; `store_entities(results, job_id, content)` and
  `mark_extraction_failed(job_id)` are new. `NER_TIMEOUT` and
  `MMT_NER_API_URL` are removed.
- `app/mmt/settings/base.py`: `CELERY_RESULT_BACKEND`.

## Slices

### Slice 1: Celery task in the NER service

- [x] 2026-10-04 Move the extraction into `extraction.py`, add `tasks.py` with the retry
  options, and add the dependency. The image still
  starts uvicorn.
  Done when: `test_api.py` passes, with only its patch targets moved from
  `api` to `extraction`; and a test calls `extract_entities` with the batches
  of `EXAMPLE_REQUEST` and receives one span list per batch.

### Slice 2: app uses the worker

The NER container is replaced before the app is deployed. Extractions that run
during the switch fail.

- [x] 2026-10-04 Add `EntityExtractionJob` with its migration, `store_entities` and
  `mark_extraction_failed`; change `enrich_transcript` to create the job and
  send the task. Convert the `enrich_transcript` tests in `test_tasks.py` to
  pytest style.
  Done when: tests show that `enrich_transcript` creates a `queued` job and
  calls `send_task` with the batch words, the `ner` queue, the job's task id, a
  `store_entities` link and a `mark_extraction_failed` error link; that
  `store_entities` creates the NER transcript with its mentions and marks the
  job `succeeded`; that two calls for the same job create one transcript; that
  invalid spans raise `ValidationError`, create no transcript and mark the job
  `failed`; and that `mark_extraction_failed` stores the exception and does not
  change a `succeeded` job.
- [x] 2026-10-04 Add `CELERY_RESULT_BACKEND` and the admin.
  Done when: the admin lists the jobs with their status.
- [ ] Switch the image `CMD` and the health check, and update
  `docker-compose.yml` (broker URL, `depends_on: redis`), `deploy/create-mmt-ner`
  (`--env CELERY_BROKER_URL`, `--env CELERY_RESULT_BACKEND`, no published port), `deploy/README.md` and
  `env.list` (no `NER_API_URL`).
  Done when: in the compose stack, two extractions started at the same time
  both create a NER transcript; an extraction whose NER container is
  restarted during inference creates its transcript after the restart; and an
  extraction whose task raises on every attempt ends as `failed` with the error after the fourth attempt.
- [x] 2026-10-06 Remove the HTTP API.
  Done when: `api.py`, `test_api.py` and the FastAPI dependencies are gone; the
  extraction tests pass against `extract()` in `test_extraction.py`; and
  `examples/evaluate.py` runs without a server.
