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
service implements by hand: the status and progress of a job, and an automatic
retry after a failure.

## Non-goals

- **No change to the ASR service.**
- **No status in the user interface.** The status and progress of an
  extraction are shown only in the Django admin.
- **No resumption of a retried job.** A retry runs all batches again from the
  first one.
- **No time limit on the NER task.**
- **No removal of the HTTP API.** `ner/api.py` and its tests stay in the
  repository, but the image no longer starts it.
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
   `results` of the HTTP API. While it runs, it reports its progress to the
   result backend.
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
"Queued", "Succeeded" and "Failed". The database stores only these durable
states. The states of a running job are read from the result backend (see
below).

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

### Progress and running states

`EntityExtractionJob.live_state()` returns a dict
`{'state': str, 'done': int | None, 'total': int | None}`:

- For a job with status `succeeded` or `failed`, `state` is the status, and
  `done` and `total` are `None`. The result backend is not queried.
- For a job with status `queued`, it reads `AsyncResult(str(task_id))` from the
  app's result backend and maps the Celery state:

| Celery state | `state` | `done`, `total` |
| --- | --- | --- |
| `PENDING` | `queued` | `None` |
| `STARTED` | `running` | `0`, `None` |
| `PROGRESS` | `running` | from the meta |
| `RETRY` | `retrying` | `None` |
| `SUCCESS`, `FAILURE` | `queued` | `None` |

`SUCCESS` and `FAILURE` map to `queued` because the callback that writes the
final status has not yet run.

### Retry

`ner.extract` is declared with:

| Option | Value |
| --- | --- |
| `bind` | `True` |
| `autoretry_for` | `(Exception,)` |
| `max_retries` | `3` |
| `retry_backoff` | `True` (1, 2, 4 seconds) |
| `retry_backoff_max` | `600` |
| `retry_jitter` | `True` |

A retry sends the job again with the same task id and the same `link` and
`link_error` signatures.

### Progress reporting

`extraction.extract` takes an optional argument
`on_batch: Callable[[int, int], None] | None = None`, called after each batch
with the number of finished batches and the total number of batches.
`extract_entities` passes a function that calls
`self.update_state(state='PROGRESS', meta={'done': done, 'total': total})`.

### Admin

`EntityExtractionJobAdmin` is read-only, like `TranscriptionJobAdmin`. The
list shows `transcript`, `status`, `live_state` and `created_at`, and filters by
`status` and `created_at`. `live_state` is shown as `running (3/12)`,
`running`, `retrying`, `queued`, `succeeded` or `failed`. The detail page shows
all fields.

### Worker configuration

[`ner/tasks.py`](../ner/tasks.py) defines `app = Celery('ner')` with:

| Setting | Value |
| --- | --- |
| `broker_url` | environment variable `CELERY_BROKER_URL` |
| `task_acks_late` | `True` |
| `task_reject_on_worker_lost` | `True` |
| `worker_prefetch_multiplier` | `1` |
| `result_backend` | environment variable `CELERY_RESULT_BACKEND` |
| `task_track_started` | `True` |

Redis delivers an unacknowledged message again after `visibility_timeout`,
which stays at its default of 1 hour on both sides. A NER task must finish
within that time.

The app gets the setting `CELERY_RESULT_BACKEND` from the environment variable
of the same name, with the same value as in the NER service. Both use the
existing Redis. `result_expires` stays at its default of 1 day; the durable
status is in the database.

The image `CMD` is `celery -A tasks worker -Q ner -n ner@%h --concurrency=1 -l INFO`.
The health check is `celery -A tasks inspect ping -d ner@$HOSTNAME`.

## File layout

- `ner/extraction.py`: `extract(batches, threshold=DEFAULT_THRESHOLD, window=WINDOW, overlap=OVERLAP, on_batch=None) -> list[list[dict]]`,
  moved out of the `/extract` route, which calls it.
- `ner/tasks.py`: the Celery app and `extract_entities(self, batches)`,
  registered as `ner.extract`.
- `ner/pyproject.toml`: adds `celery[redis]~=5.5`, the same version as the app.
- `app/mmt/transcripts/models.py`: `EntityExtractionJob` with `live_state()`.
- `app/mmt/transcripts/admin.py`: `EntityExtractionJobAdmin`.
- `app/mmt/transcripts/tasks.py`: `enrich_transcript` creates the job and sends
  the task; `store_entities(results, job_id, content)` and
  `mark_extraction_failed(job_id)` are new. `NER_TIMEOUT` and
  `MMT_NER_API_URL` are removed.
- `app/mmt/settings/base.py`: `CELERY_RESULT_BACKEND`.

## Slices

### Slice 1: Celery task in the NER service

- [ ] Move the extraction into `extraction.py`, add `tasks.py` with the retry
  options and progress reporting, and add the dependency. The image still
  starts uvicorn.
  Done when: `test_api.py` passes unchanged; a test calls `extract_entities`
  with the batches of `EXAMPLE_REQUEST` and receives one span list per batch; a
  test shows that `on_batch` is called once per batch with `(done, total)`; and
  a test shows that `extract_entities` calls `update_state` with the `PROGRESS`
  meta.

### Slice 2: app uses the worker

The NER container is replaced before the app is deployed. Extractions that run
during the switch fail.

- [ ] Add `EntityExtractionJob` with its migration, `store_entities` and
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
- [ ] Add `live_state()`, `CELERY_RESULT_BACKEND` and the admin.
  Done when: tests show the mapping of each Celery state in the table to
  `live_state()` with a patched `AsyncResult`, and that a job with a durable
  final status does not query the result backend.
- [ ] Switch the image `CMD` and the health check, and update
  `docker-compose.yml` (broker URL, `depends_on: redis`), `deploy/create-mmt-ner`
  (`--env CELERY_BROKER_URL`, no published port), `deploy/README.md` and
  `env.list` (no `NER_API_URL`).
  Done when: in the compose stack, two extractions started at the same time
  both create a NER transcript; the admin shows one as `queued` and the other
  as `running (n/m)` with increasing `n`; an extraction whose NER container is
  restarted during inference creates its transcript after the restart; and an
  extraction whose task raises on every attempt shows `retrying` and ends as
  `failed` with the error after the fourth attempt.
