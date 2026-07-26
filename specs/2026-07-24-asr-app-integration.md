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
that shape, so the ingest validates it with `validate_whisper_input` and converts
it with `normalize_content`, the same path a manual upload takes.

[`2026-07-25-transcript-language-in-content.md`](2026-07-25-transcript-language-in-content.md)
is implemented as of 2026-07-25. The `Transcript` model therefore no longer has a
`language` column, and `normalize_content` carries the whisper result's top-level
`language` into the mmt content it produces. The ingest below relies on that and
sets no language of its own.

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
- **No automatic resubmission on `404`.** A job the service no longer knows is
  marked `failed`; the user re-runs it by submitting a new transcription. The
  service keeps its spool on a persistent volume, so this state is not expected
  in normal operation.

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
| `succeeded` | copy `started_at`, `finished_at`; fetch the result, ingest it, status becomes `succeeded` |
| `failed` | copy `error`, `started_at`, `finished_at`; status becomes `failed` |
| HTTP `404` | status becomes `failed` (see below) |

Ingest on `succeeded`: `GET {ASR}/jobs/{id}/result` with a 300 s timeout, then
`validate_whisper_input` followed by `normalize_content(result).model_dump()`,
the identical path a manual whisperX upload takes
(`app/mmt/uploaded_files/forms.py`). `validate_whisper_input` raises
`ValidationError` on malformed output; `normalize_content` assumes
already-validated input and returns the mmt `Transcript` model, stored as JSON
via `.model_dump()`. The `Transcript` is created with
`uploaded_file=job.uploaded_file`, `label='ASR'`, and the content produced
above. The detected language is already in that content, because
`normalize_content` carries the result's top-level `language` into it, and the
`Transcript` model has no language field, so the ingest passes no language
argument. The job is linked to it and marked
`succeeded` with `progress` 1.0. A validation error marks the job `failed` with the exception in
the decided error format and does not create a transcript.

A `404` means the service does not have this job. The service keeps its spool on
a persistent volume, so a restart does not lose jobs and this is not expected in
normal operation; it indicates the job was removed or the volume was reset. The
sweep marks the job `failed` with the error
`The transcription service does not know this job.` Automatic resubmission is out
of scope for the first iteration; a job in this state is re-run by submitting a
new transcription from the UI.

Error strings written by the app use one line in the service's format,
`f'{type(exc).__name__}: {exc}'`.

### Beat schedule

`CELERY_BEAT_SCHEDULE` in `mmt/settings.py` runs `sweep_transcription_jobs`
every 60 seconds. Beat is expected to serve future periodic tasks as well, not
only this sweep, so the schedule is a settings-level dict rather than a
decorator on the task.

The deployment runs beat as `-B` on the worker in
[`deploy/create-mmt-app-celery`](../deploy/create-mmt-app-celery), rather than as
a separate beat process. The container runs a single Celery worker node with a
process pool (`--concurrency=4`). `-B` embeds beat in that node's main process,
so beat runs exactly once regardless of the pool size; raising the concurrency
adds worker processes but not a second beat. Per the Celery manual, `-B` is
convenient only while there is never more than one worker node and is not
recommended for production; that tradeoff is accepted at this scale (see the
recorded observations below). A second beat would only appear if a second worker
node were started, for example a second container. If the deployment is ever
scaled that way, beat moves into its own process as part of that change.

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
- The form posts `language` (a select over `WHISPERX_LANGUAGES` plus an
  empty "detect automatically" option) and `diarize` (a checkbox). The view
  creates the job with those values and calls `submit_transcription_job.delay`.
- The file's page lists the file's jobs with status, progress as a percentage,
  the error of a failed job, and a link to the produced transcript. All strings
  are translated in `locale/de/LC_MESSAGES/django.po`.

### Where a job appears

A job is visible in three places: the uploaded file's detail page, the project's
detail page while the job is still running, and the Django admin. No other view
refers to a job. The transcript detail page in particular does not link back to
the job that produced it; the link exists only in the direction from the job to
the transcript.

The file page is described here, the project page under "Project overview"
below.

On the file's page the job list and the trigger form share one `section`
element with the heading "Transcriptions". It is placed after the existing
"Transcripts" section and before the horizontal rule that precedes the delete
form. The whole section, the job list included, is rendered only for a user who
holds `transcripts.add_transcriptionjob`. This follows the pattern of the
"Transcripts" section, which is rendered only for a user who holds
`transcripts.add_transcript`.

The list shows all jobs of the file, newest first, which is the model's
`Meta.ordering`. There is no limit and no pagination, because a file collects
few jobs.

A row shows the creation date, the status, the progress, and, for a failed job,
the error. The status is rendered with the existing `pill` component, using the
semantic modifier classes that already exist in
[`assets/css/components/pill.css`](../app/assets/css/components/pill.css), so
this feature adds no CSS: `pending` uses `pill--quiet`, `submitted` and
`running` use `pill--info`, `succeeded` uses `pill--success`, and `failed` uses
`pill--danger`. The label comes from `get_status_display`. Progress is rendered
as an integer percentage, that is `progress` multiplied by 100 and rounded, and
only for a job whose status is `submitted` or `running`; a job in any other
status shows no progress, because the value carries no information there. The
row of a succeeded job links its transcript.

The trigger form is placed below the list. It is rendered only when the file has
no job in a non-terminal state, so the case that the view rejects is not offered
in the interface.

### Project overview

Opening every file of a project to find out whether it has been transcribed is
impractical, so the project's detail page carries two additions.

The first is a "Transcripts" column in
[`projects/_file_table.html`](../app/mmt/projects/templates/projects/_file_table.html),
between the existing "Status" and "Uploaded" columns. It shows the number of
transcripts of the file, and `-` for a file that has none. The column counts
every transcript, whether it came from a manual upload or from a job, because
the reader's question is which files already have a transcript. It is rendered
only for a user who holds `transcripts.view_transcript`; the header cell is
omitted for everyone else, so the table keeps a consistent column count.
The count comes from an
`annotate(transcript_count=Count('transcripts'))` on the queryset in
[`projects/views.py`](../app/mmt/projects/views.py), so the number of queries
does not grow with the number of files.

The second is a "Transcriptions" section listing the project's jobs whose status
is `pending`, `submitted` or `running`, placed after the "Uploaded files"
section and before "Downloadable files". The section is rendered only for a user
who holds `transcripts.add_transcriptionjob`, and only when there is at least
one such job; there is no empty state, so the section is absent while nothing is
running. A row shows the file name as a link to the file's page, the status pill,
the progress as an integer percentage, and the creation date. The query is
`TranscriptionJob.objects.filter(uploaded_file__project=project,
status__in=('pending', 'submitted', 'running')).select_related('uploaded_file')`.

Terminal jobs are deliberately not listed here. A succeeded job is represented
by its transcript, which the new column counts, and a failed job is visible on
the file's page, which the section's rows link to while the job still runs.

The existing "Transcripts" section on the file's detail page is rendered under
`transcripts.add_transcript` rather than `view_transcript`. That is left as it
is; changing it is not part of this feature.

### Group permissions

The `transcriptionjob` permissions are added to the Transcribers group by
[`my_account/management/commands/creategroups.py`](../app/mmt/my_account/management/commands/creategroups.py),
in the same way the command already adds the `transcript` permissions: the
content type is fetched and its full permission set is added to the group. The
command stays idempotent, so it grants the new permissions to an existing
Transcribers group on the next run of an existing deployment. The Uploaders
group is unchanged.

### Language options

`WHISPERX_LANGUAGES` is a constant in the transcripts app listing the languages
WhisperX has alignment models for, matching WhisperX's
`DEFAULT_ALIGN_MODELS_TORCH` and `DEFAULT_ALIGN_MODELS_HF`. These are the 30
codes, with the same display names, that the removed
`Transcript.LANGUAGE_CHOICES` held apart from `other`:

```
de en fr es it ja zh nl uk pt ar cs ru pl hu
fi fa el tr da he vi ko ur te hi ca ml no nn
```

The list is written out here because the model column it used to come from was
dropped by
[`2026-07-25-transcript-language-in-content.md`](2026-07-25-transcript-language-in-content.md).
`Project.LANGUAGE_CHOICES` in
[`app/mmt/projects/models.py`](../app/mmt/projects/models.py) still holds these
30 codes with their translated names and can be copied from, leaving out its
`None`, `other` and `mixed` entries.

`WHISPERX_LANGUAGES` is the single source for the transcribe form's options and
must be updated when the service upgrades WhisperX. A language outside this set has no alignment model, so a job
in it would produce output without word timestamps and fail ingest. Auto-detect
(the empty option) can still land on such a language, which the service reports
as a failed job.

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
app/mmt/my_account/
  management/commands/creategroups.py    # + the transcriptionjob permissions
  tests/test_commands.py                 # + the expected Transcribers perms
app/mmt/projects/
  views.py                               # + the transcript count and active jobs
  templates/projects/_file_table.html    # + the Transcripts column
  templates/projects/project_detail.html # + the Transcriptions section
  tests/test_project_transcriptions.py
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
  `validate_whisper_input` and `normalize_content`, and a `Transcript` is created,
  linked to the job and to the uploaded file, with `progress` 1.0; `started_at`
  and `finished_at` are copied from the status response, including when the job
  moves straight from `queued` to `succeeded`.
- **`test_sweep_stores_the_detected_language_in_the_content`** — the result's
  top-level `language` appears in the created transcript's content.
- **`test_sweep_records_invalid_content_as_a_failure`** — a validation error
  marks the job `failed` and creates no transcript.
- **`test_sweep_records_a_failed_job`** — the service's `error` is stored, the
  job becomes `failed`, and `started_at` and `finished_at` are copied from the
  status response.
- **`test_sweep_fails_on_404`** — a `404` marks the job `failed` with the error
  `The transcription service does not know this job.` and issues no resubmission.
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
- **`test_the_file_page_hides_the_trigger_while_a_job_runs`** — a file with a
  `running` job renders the job list but no trigger form.

### `projects/tests/test_project_transcriptions.py` — project overview

- **`test_the_file_table_shows_the_transcript_count`** — a file with two
  transcripts shows `2`, a file without one shows `-`.
- **`test_the_transcript_column_is_hidden_without_the_permission`** — a user
  without `transcripts.view_transcript` sees neither the header nor a count.
- **`test_the_project_page_lists_running_jobs`** — a `running` job of the
  project is listed with its file name and its progress, and a job of another
  project is not.
- **`test_terminal_jobs_are_not_listed`** — a project whose only job is
  `succeeded` renders no "Transcriptions" section.

### `my_account/tests/test_commands.py` — groups

The existing test of `creategroups` is extended: the Transcribers group holds
the four `transcript` permissions and the four `transcriptionjob` permissions
after the first run, and the same eight after a second run.

## Slices and tasks

Each slice leaves the system working and independently deployable. Each task is
one session.

- [x] **1 `TranscriptionJob` model and settings.** (2026-07-26) The model, its
  migration, a read-only admin registration, and `MMT_ASR_API_URL` beside
  `MMT_NER_API_URL`. Done when `tests/test_transcription_jobs.py` passes and the
  admin page for a job loads.
- [x] **2 Submit task and sweep poller.** (2026-07-26) Both tasks per the
  mapping table above, with the beat schedule in settings. Done when
  `tests/test_asr_tasks.py` passes.
- [x] **3 Beat in deployment.** (2026-07-26) `-B` on the worker in
  `deploy/create-mmt-app-celery`, `ASR_API_URL` in `docker/env.list`, and the
  deploy README updated. Done when the compose run brings up beat and the sweep
  is visible in the worker log in a dev run.
- [x] **4 Trigger and UI.** (2026-07-26) The view, the form, the route, the file
  page section, the `transcriptionjob` permissions in `creategroups`, and the
  German translations. Done when `tests/test_transcribe_view.py` and
  `my_account/tests/test_commands.py` pass, and a dev run transcribes an
  uploaded file end to end, producing a linked transcript.
- [x] **5 Project overview.** (2026-07-26) The "Transcripts" column in the file
  table, the "Transcriptions" section on the project page, and the German
  translations. Done when `projects/tests/test_project_transcriptions.py` passes
  and a dev run shows a running job on the project page and the transcript count
  after it finished.

## Open issues

Found in an assessment against the service spec and the codebase on 2026-07-24.
All of the assessment's issues have since been resolved in the feature reference.
Two observations remain, recorded but not blocking: the "no second non-terminal
job" check in the view is a check followed by a create, without a database
constraint, so two simultaneous requests could both pass the check; acceptable
at this scale. Celery beat's default scheduler writes a `celerybeat-schedule`
file in the container's working directory, which is lost on restart; harmless
for a pure interval schedule. Beat runs embedded in the worker via `-B`, which
the Celery manual notes is not recommended for production and is safe only while
a single worker node runs; acceptable at this scale, and revisited if a second
worker node is ever added.

## Assumptions

- The app and the ASR service see the same media storage, the app's
  `MMT_USER_FILES_DIR` and the service's `MEDIA_ROOT` being the same directory,
  so a path is all that is transferred.
- The service is reachable on the private network at `ASR_API_URL`, without
  authentication, like the NER service.
- Exactly one Celery worker node runs (a single container with a process pool),
  so `-B` on it means exactly one beat. Additional pool processes from
  `--concurrency` do not add a second beat.
