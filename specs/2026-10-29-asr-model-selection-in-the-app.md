# Spec: model selection in the app

Status: done.

This document is an **executable spec**: it is the prompt an implementing
session works from and the authoritative record of every decision. Resolve
ambiguity by reading this document, not by inventing. Check off tasks (`[x]`,
with date) as they land.

## Motivation

The ASR service offers several whisper models from its registry
(spec `2026-10-28-asr-model-selection.md`), but the app submits every job
without `model`, so every job runs with the default model. The user is to
choose the model when starting a transcription.

The list of models is configured in the service, not in the app, so the app
reads it from the service. The app reads the other properties of the service
with the same request: its version, and whether diarization is possible. The
submit task marks a job as failed when the service cannot be reached, so the
form is not offered while the service does not answer.

## Non-goals

- **No display in the admin.** The service status page (spec
  `2026-09-18-service-status-page.md`) is the place to show the service
  information to staff. Changing that spec to read `GET /info` is a separate
  change.
- **No Celery transport.** If the ASR service becomes a Celery worker, the
  information is read with a custom inspect command
  (`celery_app.control.inspect(timeout=1.0, limit=1).asr_info()`) instead of
  `GET /info`. Only `asr_info()` in `mmt/transcripts/asr.py` knows the
  transport, so the switch changes that function only.
- **No change of the model of an existing job**, and no recording of the model
  the result reports.

## Feature reference

### Cache backend

The app has no `CACHES` setting yet, so each process would cache on its own,
and two processes could disagree on whether the service is available. The
default cache becomes Redis, on the instance that already serves as the Celery
broker:

- `CACHES['default']` is `django.core.cache.backends.redis.RedisCache` with
  `LOCATION = os.environ['CACHE_URL']`. The variable is required, as
  `CELERY_BROKER_URL` is.
- `docker/env.list` sets `CACHE_URL=redis://redis/1`, a database separate from
  the broker's. `app/.env.example` sets `CACHE_URL=redis://localhost/1`.
  `app/Dockerfile` and the CI workflow set it where they set
  `CELERY_BROKER_URL`. `deploy/README.md` lists the variable.
- Every Celery Redis URL names database 0 explicitly (`redis://redis/0`,
  `redis://localhost/0`, `redis://mmt-redis/0`), so that both databases are
  visible in the configuration. This applies to `CELERY_BROKER_URL` and
  `CELERY_RESULT_BACKEND` in `docker/env.list`, `docker/docker-compose.yml`,
  `podman/mmt-ner.container`, `app/.env.example`, `app/Dockerfile`, the CI
  workflow, `deploy/README.md` and `ner/README.md`.
- The test settings use `django.core.cache.backends.locmem.LocMemCache`. An
  autouse fixture in `app/conftest.py` clears the cache before each test.

### `GET /info` in the ASR service

`GET /info` replaces `GET /models`, which no client uses yet:

```json
{
  "version": "0.5.0",
  "diarization": true,
  "default_model": "large-v3",
  "models": [
    {"name": "large-v3", "description": "Whisper large-v3"},
    {"name": "large-v3-verbatim-v1", "description": "large-v3, fine-tuned for verbatim transcription"}
  ]
}
```

- `version` is the content of `asr/VERSION`, as in `GET /health`.
- `diarization` is true when `HF_TOKEN` is set.
- `default_model` and `models` are the former content of `GET /models`.
- `GET /health` is unchanged and stays the container health check.
- The ASR version becomes `0.5.0`.

### `asr_info()` in the app

```python
# mmt/transcripts/asr.py
@dataclass(frozen=True)
class AsrModel:
    name: str
    description: str

@dataclass(frozen=True)
class AsrInfo:
    version: str
    diarization: bool
    default_model: str
    models: tuple[AsrModel, ...]

def asr_info() -> AsrInfo | None: ...  # None: the service is unavailable
```

- Requests `GET {MMT_ASR_API_URL}/info` with a timeout of 2 seconds.
- A `requests.RequestException`, a non-2xx status or a body without the fields
  above counts as unavailable.
- The result is stored in the Django default cache under the key `asr_info`:
  an available result for 300 seconds, an unavailable result for 30 seconds.
  The unavailable result is stored as a marker value, so that a cache miss and
  an unavailable service are distinguishable.

### Job model

`TranscriptionJob` gets `model = CharField(max_length=100, blank=True,
verbose_name=_('Model'))`. Jobs created before this feature have an empty
value. Every new job stores the name of the chosen model.
`TranscriptionJobAdmin` shows `model` in `list_display` and `fields`.

`task_submit_transcription_job` sends `model` in the request body when the
field is not empty.

### Form

- `TranscriptionJobForm(*args, info: AsrInfo | None = None, **kwargs)`.
- `model` is the model field of `TranscriptionJob`, labelled "Model" and
  rendered as a `Select` widget.
- With `info`, the widget has one choice per entry of `info.models` in the
  order of the service. Value and label of a choice are the model name. The
  initial value is `info.default_model`.
- Without `info`, as in `transcribe`, the form accepts any string of at most
  100 characters. The service rejects an unknown name with `400`, and the
  submit task marks the job failed.
- With `info.diarization` false, the form has no `diarize` field and the job
  stores `diarize = False`.

### Views

- `detail` calls `asr_info()` only when `MMT_ASR_ENABLED` is true and the user
  holds `transcripts.add_transcriptionjob`. When the result is `None`, the
  transcription section shows the job table as before and, in place of the
  form, the sentence "Transcription is currently unavailable." Otherwise the
  template receives `TranscriptionJobForm(info=info)`.
- `transcribe` does not call `asr_info()`. It is unchanged apart from the
  `model` field of the form.

### Translations

German translation for "Transcription is currently unavailable." "Model" is
already translated.

## File layout

```
asr/api.py                                   # GET /info replaces GET /models
asr/VERSION                                  # 0.5.0
app/mmt/settings/base.py                     # CACHES from CACHE_URL
app/mmt/settings/test.py                     # LocMemCache
app/conftest.py                              # autouse fixture: cache.clear()
app/.env.example, app/Dockerfile             # CACHE_URL, Celery URLs with /0
docker/env.list                              # CACHE_URL=redis://redis/1, Celery URLs with /0
docker/docker-compose.yml                    # Celery URLs with /0
podman/mmt-ner.container                     # Celery URLs with /0
.github/workflows/app-tests.yml              # CACHE_URL, Celery URL with /0
deploy/README.md                             # CACHE_URL in the variable list, /0
ner/README.md                                # Celery URLs with /0
app/mmt/transcripts/asr.py                   # new: AsrModel, AsrInfo, asr_info()
app/mmt/transcripts/models.py                # + TranscriptionJob.model
app/mmt/transcripts/migrations/00xx_...      # the new field
app/mmt/transcripts/admin.py                 # model in list_display and fields
app/mmt/transcripts/tasks.py                 # model in the submit body
app/mmt/uploaded_files/forms.py              # TranscriptionJobForm(info, ...)
app/mmt/uploaded_files/views.py              # detail, transcribe
app/mmt/uploaded_files/templates/uploaded_files/detail.html
```

## Slices and tasks

### Slice 0: cache backend

- [x] (2026-10-31) `CACHES` from `CACHE_URL`, `LocMemCache` in the test settings, the
  autouse fixture that clears the cache, `CACHE_URL` and the explicit `/0` in
  every file listed under "Cache backend". Done when the suite passes in CI
  with `CACHE_URL` set, and no Celery Redis URL in the repository lacks a
  database number.

### Slice 1: `GET /info` in the ASR service

- [x] (2026-10-31) Replace `GET /models` with `GET /info`, update the API descriptions and
  `asr/README.md`, set `asr/VERSION` to `0.5.0`. Done when `test_api.py`
  asserts the full `GET /info` body for a registry with two models, with and
  without `HF_TOKEN`.

### Slice 2: `asr_info()` and the job field

- [x] (2026-10-31) `mmt/transcripts/asr.py`, the `model` field with its migration and admin
  entry, `model` in the submit body. Done when tests with the HTTP call
  patched assert that `asr_info()` returns the parsed information, returns
  `None` for a connection error, a `500` and a body without `models`, caches
  both outcomes so that a second call makes no request, and when the submit
  task test asserts that `model` is sent when set and absent when empty.

### Slice 3: form and views

- [x] (2026-10-31) The form, the two views, the template and the translations. Done when
  view tests with `asr_info` patched assert that the detail page offers the
  models with the default selected, has no diarize field without diarization
  and shows the unavailable sentence for `None`; and that `transcribe` stores
  the chosen model.
