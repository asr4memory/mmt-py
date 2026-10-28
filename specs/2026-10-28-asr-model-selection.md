# Spec: selectable models in the ASR service

Status: not started.

This document is an **executable spec** (spec-driven development): it is the
prompt an implementing session works from and the authoritative record of every
decision. Resolve ambiguity by reading this document, not by inventing; if a
genuinely new decision comes up, write it into this document as part of the
task. Check off tasks (`[x]`, with date) as they land. Do not duplicate
CLAUDE.md conventions here.

## Motivation

The ASR service runs one whisper model, named by `WHISPERX_MODEL`. A
fine-tuned model based on `large-v3` that transcribes more verbatim, stored as
a local directory, is to be offered next to `large-v3`. The two models need
different settings (compute type, batch size), so a list of names in an
environment variable is not enough. The service reads a registry of models
from a TOML file, and the caller selects a model per job by its name. The file
is configured like the configuration of an nginx container: the image ships a
working file at a fixed path, and the operator mounts their own file over it.

## Non-goals

- **No model selection in the Django app.** The app keeps submitting jobs
  without `model` and receives the default model. Selection in the app is a
  separate spec.
- **No reloading of the registry at run time.** A change to the file takes
  effect after a restart of the service.
- **No more than one loaded whisper model.** GPU memory use stays that of the
  largest configured model.
- **No per-job settings.** `compute_type` and `batch_size` belong to a model,
  not to a job.
- **No upload or conversion of models through the API.** A local model is a
  CTranslate2 directory placed on the host by the operator.

## Feature reference

### Registry file

The service reads the registry from `MODELS_FILE`, which defaults to
`/etc/mmt-asr/models.toml`. Example:

```toml
default = "large-v3"

[models.large-v3]
source = "large-v3"
compute_type = "float16"
batch_size = 16
description = "Whisper large-v3"

[models.large-v3-verbatim-v1]
source = "/models/large-v3-verbatim-v1"
compute_type = "int8_float16"
batch_size = 8
description = "large-v3, fine-tuned for verbatim transcription"
```

- Top-level keys: `default` (required), `models` (required, at least one
  entry). No other keys.
- Model keys: `source` (required), `compute_type` (default `"float16"`),
  `batch_size` (default `16`), `description` (default `""`). No other keys.
- A model name matches `^[a-z0-9][a-z0-9._-]*$`.
- A `source` that starts with `/` is a local path and must be an existing
  directory. Any other `source` is a Hugging Face model name and is not
  checked.
- `default` must name an entry of `models`.
- Entries keep the order of the file.
- Any violation raises `RegistryError` with a message naming the key or model.
  The service then does not start.

The registry file is the only place where models are configured.
`WHISPERX_MODEL`, `WHISPERX_COMPUTE_TYPE` and `WHISPERX_BATCH_SIZE` are
removed. `WHISPERX_DEVICE` stays and applies to every model.

### Shipped files

- `asr/models.toml` contains one entry, `large-v3` with `source = "large-v3"`,
  `compute_type = "float16"` and `batch_size = 16`, and names it as the
  default. These are the defaults of the removed variables, so a container
  without a mounted file behaves as before. The Dockerfile copies it to
  `/etc/mmt-asr/models.toml`.
- `asr/models.dev.toml` contains one entry, `small` with
  `source = "small"`, `compute_type = "int8"` and `batch_size = 4`, as the
  default. It is for local runs outside the container, where
  `/etc/mmt-asr` does not exist: `MODELS_FILE=models.dev.toml`. It is not
  copied into the image.

### Loading

`api.lifespan` loads the registry once, stores it in `app.state.registry` and
passes it to `start_worker`. The API and the worker use this one instance.

### Jobs

- `JobRequest` gets `model: str | None = None`. `null` selects the default.
- `POST /jobs` checks the path first, then the model. An unknown model answers
  `400` with `{"detail": "unknown model"}`.
- `job.json` gets the field `model` with the resolved name, so a later change
  of `default` does not affect queued jobs.
- `JobStatus` gets `model: str | None`. It is `null` only for jobs created
  before this feature; the worker runs these with the default model.
- At run time the worker looks the name up in the registry. A name that is no
  longer in the registry fails the job with the error
  `unknown model: <name>`, before any transcription work.
- The result's `model` field is the registry name. With the shipped file
  this is `large-v3`, as before.

### `GET /models`

```json
{
  "default": "large-v3",
  "models": [
    {"name": "large-v3", "description": "Whisper large-v3"},
    {"name": "large-v3-verbatim-v1", "description": "large-v3, fine-tuned for verbatim transcription"}
  ]
}
```

`source`, `compute_type` and `batch_size` are not returned.

### Model replacement

The transcriber keeps one loaded model together with its name. When a job
needs a different model, it deletes the reference, runs `gc.collect()`, calls
`torch.cuda.empty_cache()` when the device is `cuda`, and then loads the
requested model. A job that uses the loaded model does not reload it.

### Prefetch and deployment

- `prefetch.py` reads the same registry and loads every entry whose source is
  a Hugging Face name. Local entries are skipped. The prefetch container
  mounts the same registry file as the service.
- The registry file and the model directories are separate mounts, and
  production does not set `MODELS_FILE`:
  - The host file `MMT_ASR_MODELS_FILE` is mounted read-only over
    `/etc/mmt-asr/models.toml`.
  - The host directory `MMT_ASR_MODELS_DIR` is mounted read-only at `/models`
    and holds only model directories. A local `source` names the path inside
    the container, for example `/models/large-v3-verbatim-v1`.
  - `deploy/create-mmt-asr` adds each mount only when its variable is set,
    and no longer forwards the three removed variables.

## File layout

```python
# asr/models.py — the only module that knows the registry format
class RegistryError(Exception): ...

@dataclass(frozen=True)
class ModelSpec:
    name: str
    source: str
    compute_type: str
    batch_size: int
    description: str

@dataclass(frozen=True)
class Registry:
    default: ModelSpec
    models: tuple[ModelSpec, ...]
    def get(self, name: str | None) -> ModelSpec | None: ...  # None selects the default

def load_registry(path: Path) -> Registry: ...

# asr/config.py: whisperx_model, whisperx_compute_type, whisperx_batch_size removed
def models_file() -> Path: ...  # MODELS_FILE, default /etc/mmt-asr/models.toml

# asr/transcriber.py
Transcribe = Callable[[Path, ModelSpec, str | None, bool, Callable[[float], None]], dict]

# asr/worker.py
class Worker:
    def __init__(self, spool: Path, registry: Registry, transcribe: Transcribe, ...): ...

# asr/jobs.py
def create_job(spool, path, model: str, language, diarize) -> dict: ...

# asr/api.py
def start_worker(spool: Path, registry: Registry) -> Worker: ...
```

## Tests

- `test_models.py`: `test_a_valid_file_is_loaded_in_file_order`,
  `test_model_keys_take_their_defaults`,
  parametrized `test_the_shipped_files_are_valid` (`models.toml`,
  `models.dev.toml`),
  `test_get_none_returns_the_default`, `test_get_an_unknown_name_returns_none`,
  and parametrized `test_an_invalid_file_raises` (unknown top-level key,
  unknown model key, missing `source`, invalid name, missing local directory,
  `default` not in `models`, no models).
- `test_api.py`: `test_post_jobs_stores_the_default_model_when_none_is_given`,
  `test_post_jobs_stores_the_requested_model`,
  `test_post_jobs_rejects_an_unknown_model`,
  `test_get_job_reports_the_model`,
  `test_get_models_lists_names_and_descriptions_without_sources`; extend
  `test_create_job_writes_the_full_field_set` in `test_jobs.py`.
- `test_worker.py`: `test_the_transcriber_gets_the_jobs_model_spec`,
  `test_a_job_without_a_model_runs_with_the_default`,
  `test_a_model_missing_from_the_registry_fails_the_job`.
- `test_transcriber.py`: replace
  `test_the_model_is_loaded_from_the_environment_and_cached` with
  `test_the_model_is_loaded_with_the_specs_settings_and_cached` and
  `test_a_different_model_replaces_the_loaded_one`; adjust
  `test_the_result_names_the_model_the_transcription_ran_with` to the
  registry name; add `test_the_batch_size_comes_from_the_spec`.
- `test_prefetch.py`: `test_prefetch_loads_every_hugging_face_model_and_skips_local_ones`;
  adjust `test_main_reads_the_environment`.

## Slices and tasks

### Slice 1: registry, default model only

- [ ] `models.py`, `config.models_file()`, the shipped files and the
  Dockerfile copy. The three `WHISPERX_*` variables are removed from
  `config.py`, `deploy/create-mmt-asr` and the README. The lifespan loads the
  registry; the transcriber receives the default `ModelSpec` and takes
  `compute_type` and `batch_size` from it. The API does not change.
  Done when the `test_models.py` tests and the adjusted transcriber tests
  pass, and a container without a mounted file transcribes with `large-v3`
  as before.

### Slice 2: selection per job

- [ ] `model` in `JobRequest`, `job.json` and `JobStatus`; `GET /models`;
  registry lookup in the worker; model replacement in the transcriber;
  API description texts updated. Done when the tests listed for
  `test_api.py`, `test_jobs.py`, `test_worker.py` and `test_transcriber.py`
  pass.

### Slice 3: prefetch and deployment

- [ ] `prefetch.py` iterates the registry; `deploy/create-mmt-asr` mounts
  `MMT_ASR_MODELS_FILE` and `MMT_ASR_MODELS_DIR`; the README documents the
  file format, both mounts, `MODELS_FILE` for local runs and the CTranslate2
  requirement for local models. Done when the
  `test_prefetch.py` tests pass.
