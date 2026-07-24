# Spec: ASR app integration

Status: not started. Split out of
[`2026-07-21-asr-service.md`](2026-07-21-asr-service.md) on 2026-07-24, where it
was slice 4, because the service itself is complete through slice 3 and the app
side is a separate body of work with its own slices, tests and deployment step.

This document is an **executable spec** (spec-driven development): it is the
prompt an implementing session works from and the authoritative record of every
decision, not a background sketch. Resolve ambiguity by reading this doc, not by
inventing; if a genuinely new decision comes up, write it into the doc as part
of the task. Check off tasks (`[x]`, with date) as they land. Do not duplicate
CLAUDE.md conventions here (test-first, pytest style).

## Motivation

The ASR service transcribes media files, but nothing in the app calls it. Today
a transcript reaches the app only by a user or an admin uploading a whisperX
JSON file by hand. This slice connects the two: a user with the transcription
permission starts a job from an uploaded file's page, the app submits it to the
service, polls it, and stores the finished result as a `Transcript` on that
file.

The conversion already exists. `normalize_content` in
[`app/mmt/transcripts/normalize.py`](../app/mmt/transcripts/normalize.py) turns
lenient Whisper/whisperX JSON into mmt content, and the service returns exactly
that shape, so the ingest path is the same one a manual upload takes.

## Non-goals

Do not add these, even where they would be easy:

- **No coupling to `ProcessingRequest`.** See the decision below.
- **No cancellation from the app.** The service's `DELETE /jobs/{id}` is not
  called by any app code in this feature.
- **No retry of a failed job from the UI.** A failed job is a record; the user
  starts a new job.
- **No batch transcription** of a whole project or a file selection. One job per
  file, started explicitly.
- **No live progress push.** Progress is visible after a page reload, no
  websockets and no polling from the browser.
- **No editing of the produced transcript** beyond what the existing transcript
  views already offer.
- **No per-job model or compute settings.** `WHISPERX_MODEL` and the rest are
  service configuration; the app sends only `path`, `language` and `diarize`.

### Transcription jobs are decoupled from `ProcessingRequest`

`ProcessingRequest` is a human workflow ticket: an admin reviews it, it lists
several files and has four possible actions. A `TranscriptionJob` is machine
execution state for exactly one media file. No foreign key, no fan-out on
accept, no shared status vocabulary. If the ticket workflow is ever to create
jobs, that is a separate later decision and nothing in this feature anticipates
it.

### Polling is one beat-scheduled sweep, not per-job retry chains

A per-job `self.retry(countdown=30)` chain does not occupy a worker (it
re-enqueues with an ETA), but 20 concurrent jobs would mean 20 long-lived chains
whose only state is broker messages. Those need `max_retries=None`, stop without
a record if the broker drops a message, and offer no single place to see what is
pending. The sweep runs a constant number of tasks regardless of how many jobs
exist, keeps pending state in the database so that a missed tick is corrected by
the next one, and is straightforward to inspect. Never poll by sleeping inside a
task body, which does occupy a worker slot.

## Feature reference

### `TranscriptionJob`

Lives in `mmt/transcripts/models.py`, beside `Transcript`.

| field | type | notes |
|---|---|---|
| `uploaded_file` | FK `uploaded_files.UploadedFile`, `CASCADE` | `related_name='transcription_jobs'` |
| `transcript` | FK `Transcript`, `SET_NULL`, nullable | the produced transcript, set on success |
| `asr_job_id` | `CharField(max_length=32, blank=True)` | the service's id, empty until submitted |
| `status` | `CharField(max_length=20)`, choices below | default `pending` |
| `progress` | `FloatField(default=0.0)` | copied from the service |
| `error` | `TextField(blank=True)` | the service's error string, or the app-side reason |
| `language` | `CharField(max_length=10, blank=True)` | empty means the service auto-detects |
| `diarize` | `BooleanField(default=False)` | |
| `resubmitted` | `BooleanField(default=False)` | set when a `404` caused one resubmission |
| `created_at` | `DateTimeField(auto_now_add=True)` | |
| `updated_at` | `DateTimeField(auto_now=True)` | doubles as "last heard from the service" |
| `started_at` | `DateTimeField(null=True)` | copied from the service |
| `finished_at` | `DateTimeField(null=True)` | copied from the service |

`status` is one of `pending | submitted | running | succeeded | failed`.
`succeeded` and `failed` are terminal; the sweep never queries a terminal job
again. There is no `submitted_at`, because a non-empty `asr_job_id` encodes it.

The service owns execution time: `started_at` and `finished_at` are copied from
the status response and the app never records its own observation times, because
such a timestamp is only as precise as the polling interval.

`Meta.ordering = ['-created_at']`.

### Settings

`MMT_ASR_API_URL = env('ASR_API_URL')` in `mmt/settings.py`, beside
`MMT_NER_API_URL`. The deployment passes it in
[`docker/env.list`](../docker/env.list) like the NER URL.

### Tasks

Both in `mmt/transcripts/tasks.py`, beside `enrich_transcript`, using `requests`
as that task does.

- `submit_transcription_job(job_id: int) -> None` — `POST {ASR}/jobs` with
  `{"path": ..., "language": ..., "diarize": ...}`; timeout 30 s. `path` is the
  file's storage-relative path, `file_path.relative_to(settings.MMT_USER_FILES_DIR)`
  as a POSIX string, which is what the service resolves against its own
  `MEDIA_ROOT`. `language` is omitted from the body when the field is empty. On
  `202` it stores `asr_job_id` and sets the status to `submitted`. On `400` it
  sets the status to `failed` and stores the service's response body as the
  error. Any other error status raises, so Celery records the failure; the sweep
  does not resubmit `pending` jobs, so a lost submission stays visible as
  `pending`.
- `sweep_transcription_jobs() -> None` — for every job whose status is
  `submitted` or `running`, `GET {ASR}/jobs/{asr_job_id}`; timeout 30 s. Each
  job is handled in its own `try`/`except`, so one unreachable or malformed
  response does not stop the sweep for the remaining jobs.

The sweep maps the service's response as follows:

| service status | app action |
|---|---|
| `queued` | copy `progress`; status stays `submitted` |
| `running` | copy `progress`, `started_at`, `finished_at`; status becomes `running` |
| `succeeded` | fetch the result, ingest it, status becomes `succeeded` |
| `failed` | copy `error` and `finished_at`; status becomes `failed` |
| HTTP `404` | resubmit once, otherwise fail (see below) |

Ingest on `succeeded`: `GET {ASR}/jobs/{id}/result` with a 300 s timeout, then
`normalize_content` and `validate_mmt_content`, the identical path a manual
whisperX upload takes. The `Transcript` is created with
`uploaded_file=job.uploaded_file`, `label='ASR'`, and `language` taken from the
result's `language` key when it is one of `Transcript.LANGUAGE_CHOICES` and
`other` otherwise. The job is linked to it and marked `succeeded` with
`progress` 1.0. A validation error marks the job `failed` with the exception in
the decided error format and does not create a transcript.

A `404` means the service lost the job (its spool is not permanent storage). If
`resubmitted` is false, the sweep clears `asr_job_id`, sets `resubmitted` and
calls the submit task again; if it is already true, the job becomes `failed`
with the error `The transcription service does not know this job.`

Error strings written by the app use one line in the service's format,
`f'{type(exc).__name__}: {exc}'`.

### Beat schedule

`CELERY_BEAT_SCHEDULE` in `mmt/settings.py` runs `sweep_transcription_jobs`
every 60 seconds. Beat is expected to serve future periodic tasks as well, not
only this sweep, so the schedule is a settings-level dict rather than a
decorator on the task.

The deployment runs beat as `-B` on the existing worker in
[`deploy/create-mmt-app-celery`](../deploy/create-mmt-app-celery) while there is
exactly one worker container, rather than as a second container. A second worker
container would run a second beat and double every periodic task, so if the
worker is ever scaled out, beat moves into its own container as part of that
change.

### Trigger and UI

| method & path | name | permission | result |
|---|---|---|---|
| `POST /uploaded_files/<pk>/transcribe/` | `uploaded_files:transcribe` | `transcripts.add_transcriptionjob` | `302` back to the file's page |

- The view is `POST` only and uses
  `permission_required('transcripts.add_transcriptionjob', raise_exception=True)`,
  so a user without the permission receives `403` rather than a redirect to the
  login page. This is the app's existing authorization mechanism; the permission
  is granted in practice by putting users in a group that holds it, which is how
  the earlier "Transcribers group" wording is realized.
- The file must be owned by the requesting user's project and must have
  `has_file` true and `is_av_media` true; otherwise the view returns `404` for
  the ownership case and redirects with an error message for the other two.
- A file that already has a job in a non-terminal state (`pending`,
  `submitted`, `running`) is not submitted again: the view redirects with an
  error message. Several terminal jobs per file are allowed.
- The form posts `language` (a select over `Transcript.LANGUAGE_CHOICES` plus an
  empty "detect automatically" option) and `diarize` (a checkbox). The view
  creates the job with those values and calls `submit_transcription_job.delay`.
- The file's page lists the file's jobs with status, progress as a percentage,
  the error of a failed job, and a link to the produced transcript. All strings
  are translated in `locale/de/LC_MESSAGES/django.po`.

## File layout

```
app/mmt/transcripts/
  models.py                    # + TranscriptionJob
  tasks.py                     # + submit_transcription_job, sweep_transcription_jobs
  admin.py                     # + TranscriptionJobAdmin (read-only list)
  migrations/                  # + TranscriptionJob migration
  tests/test_transcription_jobs.py
  tests/test_asr_tasks.py
app/mmt/uploaded_files/
  views.py                     # + transcribe
  forms.py                     # + TranscriptionJobForm
  urls.py                      # + the transcribe route
  templates/uploaded_files/detail.html   # + the job list and the trigger
  tests/test_transcribe_view.py
app/mmt/settings.py            # + MMT_ASR_API_URL, CELERY_BEAT_SCHEDULE
deploy/create-mmt-app-celery   # + -B
docker/env.list                # + ASR_API_URL
```

Key signatures:

```python
# mmt/transcripts/models.py
class TranscriptionJob(models.Model):
    PENDING, SUBMITTED, RUNNING, SUCCEEDED, FAILED = (
        'pending', 'submitted', 'running', 'succeeded', 'failed')
    TERMINAL = (SUCCEEDED, FAILED)

    @property
    def media_path(self) -> str        # storage-relative POSIX path
    @property
    def is_terminal(self) -> bool

# mmt/transcripts/tasks.py
@shared_task
def submit_transcription_job(job_id: int) -> None
@shared_task
def sweep_transcription_jobs() -> None
def _ingest_result(job: TranscriptionJob, result: dict) -> None
```

## Tests

Run with `uv run pytest` from `app/`. The ASR service is never contacted: the
tests patch `requests.post` and `requests.get` in `mmt.transcripts.tasks`.

### `tests/test_transcription_jobs.py` — model

- **`test_media_path_is_relative_to_the_user_files_dir`** — a file in a project
  yields the path the service resolves against its `MEDIA_ROOT`, with no leading
  slash.
- **`test_a_new_job_is_pending_with_no_service_id`**
- **`test_is_terminal_covers_succeeded_and_failed_only`** — parametrized over
  the five statuses.

### `tests/test_asr_tasks.py` — submit and sweep

- **`test_submit_posts_the_relative_path_and_stores_the_job_id`** — the request
  body carries the storage-relative path, the language and `diarize`; the job
  becomes `submitted` with the service's id.
- **`test_submit_omits_an_empty_language`** — no `language` key in the body.
- **`test_submit_marks_the_job_failed_on_a_rejected_path`** — a `400` response
  becomes `failed` with the response body as the error, and no exception.
- **`test_sweep_copies_progress_and_timestamps`** — a `running` response updates
  `progress`, `started_at` and `finished_at` and moves the status to `running`.
- **`test_sweep_ingests_a_succeeded_job`** — the result is fetched, run through
  `normalize_content` and `validate_mmt_content`, and a `Transcript` is created,
  linked to the job and to the uploaded file, with `progress` 1.0.
- **`test_sweep_maps_an_unknown_result_language_to_other`**
- **`test_sweep_records_invalid_content_as_a_failure`** — a validation error
  marks the job `failed` and creates no transcript.
- **`test_sweep_records_a_failed_job`** — the service's `error` is stored and
  the job becomes `failed`.
- **`test_sweep_resubmits_once_on_404`** — the first `404` clears `asr_job_id`,
  sets `resubmitted` and calls the submit task; the second marks the job
  `failed`.
- **`test_sweep_leaves_terminal_jobs_untouched`** — a `succeeded` and a `failed`
  job produce no request.
- **`test_sweep_continues_after_a_request_error`** — with two non-terminal jobs
  whose first request raises, the second job is still updated.

### `tests/test_transcribe_view.py` — trigger

- **`test_transcribe_creates_a_job_and_queues_the_submit_task`** — the job
  carries the posted language and `diarize`, and the task is called with its id.
- **`test_transcribe_requires_the_permission`** — a user without
  `transcripts.add_transcriptionjob` receives `403` and no job is created.
- **`test_transcribe_action_is_hidden_without_the_permission`** — the file's
  page does not contain the trigger for such a user.
- **`test_transcribe_rejects_a_file_of_another_user`** — `404`.
- **`test_transcribe_rejects_a_file_without_media`** — a file with `has_file`
  false is redirected with an error message and creates no job.
- **`test_transcribe_refuses_a_second_running_job`** — a file with a `running`
  job creates no second job.
- **`test_the_file_page_shows_job_state`** — status, progress and the error of a
  failed job are rendered, and a succeeded job links its transcript.

## Slices and tasks

Each slice leaves the system working and independently deployable. Each task is
one session.

- [ ] **1 `TranscriptionJob` model and settings.** The model, its migration, a
  read-only admin registration, and `MMT_ASR_API_URL` beside `MMT_NER_API_URL`.
  Done when `tests/test_transcription_jobs.py` passes and the admin page for a
  job loads.
- [ ] **2 Submit task and sweep poller.** Both tasks per the mapping table
  above, with the beat schedule in settings. Done when
  `tests/test_asr_tasks.py` passes.
- [ ] **3 Beat in deployment.** `-B` on the worker in
  `deploy/create-mmt-app-celery`, `ASR_API_URL` in `docker/env.list`, and the
  deploy README updated. Done when the compose run brings up beat and the sweep
  is visible in the worker log in a dev run.
- [ ] **4 Trigger and UI.** The view, the form, the route, the file page
  section, and the German translations. Done when
  `tests/test_transcribe_view.py` passes and a dev run transcribes an uploaded
  file end to end, producing a linked transcript.

## Assumptions

- The app and the ASR service see the same media storage, the app's
  `MMT_USER_FILES_DIR` and the service's `MEDIA_ROOT` being the same directory,
  so a path is all that is transferred.
- The service is reachable on the private network at `ASR_API_URL`, without
  authentication, like the NER service.
- Exactly one Celery worker container runs, so `-B` on it means exactly one
  beat.
