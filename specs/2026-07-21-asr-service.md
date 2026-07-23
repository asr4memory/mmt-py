# Spec: ASR service

Status: slices 1 and 2 implemented up to and including task 2.3; tasks 2.4
and 2.5 open. Moved here from `docs/asr-service-plan.md` on 2026-07-21 and
adapted to the spec format. The same move changed one implemented decision:
model weights are no longer baked into the image (see
[Model weights and the Hugging Face cache](#model-weights-and-the-hugging-face-cache)),
which reopens part of the Dockerfile written in task 2.2.

This document is an **executable spec** (spec-driven development): it is the
prompt an implementing session works from and the authoritative record of every
decision, not a background sketch. Resolve ambiguity by reading this doc, not by
inventing; if a genuinely new decision comes up, write it into the doc as part
of the task. Check off tasks (`[x]`, with date) as they land. Do not duplicate
CLAUDE.md conventions here (test-first, pytest style).

## Motivation

Transcription is currently a manual step: a user files a `ProcessingRequest`, an
admin runs whisperX by hand and uploads the result. A transcription service
closes that loop the same way the NER service did for entity extraction: a
small, self-contained FastAPI capability — media in, transcript out — that the
app drives from Celery.

Like the NER service, the ASR service is **format-agnostic**. It returns
whisperX's native output and knows nothing about the mmt-transcript format. The
app already converts lenient Whisper/whisperX JSON into mmt content
(`normalize_content` in [`app/mmt/transcripts/normalize.py`](../app/mmt/transcripts/normalize.py)),
so the service output plugs straight into the existing ingest path.

The one structural difference from NER: transcription of an hour of media takes
minutes to hours, which is far longer than an HTTP request should be held open,
and the model must process jobs serially (one GPU, one model instance). So the
service is asynchronous around a **job queue**: submit, poll, fetch result.

## Non-goals (v1)

Do not add these, even where they would be easy:

- **No auth.** Private network, same as the NER service.
- **No webhooks or callbacks.** The app polls; the service never initiates
  connections.
- **No cancellation of running jobs.** `DELETE` on a running job only marks it
  for cleanup after it finishes.
- **No priorities or reordering.** Strict FIFO by submission time.
- **No file upload endpoint.** Media is referenced by path on shared storage
  only.
- **No mmt-transcript knowledge.** The service never sees or produces mmt
  format, ids, or versions.
- **No concurrency.** One worker thread, one job at a time, `--workers 1`.
- **No result archive.** Retention is a safety margin for slow pollers, not
  storage.

## Feature reference

### Endpoints

| method & path | success | errors |
|---|---|---|
| `POST /jobs` | `202` job created | `400` path missing on disk or outside `MEDIA_ROOT`; `422` malformed body (FastAPI default) |
| `GET /jobs/{id}` | `200` status object | `404` unknown id |
| `GET /jobs/{id}/result` | `200` whisperX JSON | `404` unknown id; `409` job not `succeeded` |
| `DELETE /jobs/{id}` | `204` | `404` unknown id |

Unknown ids are `404` also after service data loss; callers treat `404` as
"gone, resubmit".

### `POST /jobs`

JSON body referencing the media file on shared storage. The media volume is
reachable by all systems, so no media bytes are transferred over HTTP.

```json
{"path": "user_files/abc/interview.mp4", "language": "de", "diarize": false}
```

| field | type | notes |
|---|---|---|
| `path` | string | relative to `MEDIA_ROOT`; any format ffmpeg can read |
| `language` | string, optional | ISO 639-1; omitted means whisper auto-detects |
| `diarize` | bool, default `false` | speaker diarization (slice 3) |

The path is resolved against `MEDIA_ROOT` and must stay inside it. A file that
does not exist at submit time is rejected, so a wrong path is reported in the
response to the submitting call rather than when the job reaches the front of
the queue. The worker checks again at run time, because the file can be deleted
while the job is queued, and marks the job `failed` if it is gone.

Response `202`:

```json
{"id": "j_8f3ab2c1", "status": "queued"}
```

### `GET /jobs/{id}`

```json
{"id": "j_8f3ab2c1", "status": "running", "progress": 0.65,
 "created_at": "2026-07-08T14:02:11+00:00",
 "started_at": "2026-07-08T14:05:03+00:00", "finished_at": null,
 "language": "de", "error": null}
```

`status` is one of `queued | running | failed | succeeded`. `progress` is a
fraction in `[0, 1]`: `0` while queued, monotonically increasing while running,
`1` when succeeded. Failed jobs carry an `error` string. `started_at` and
`finished_at` are taken from `job.json` and are null until reached. Callers copy
them rather than recording the time at which they observed the change, because
such a timestamp is only as precise as the polling interval.

### `GET /jobs/{id}/result`

Only valid for `succeeded` jobs (`409` otherwise). Returns whisperX's aligned
output as-is:

```json
{
  "language": "de",
  "segments": [
    {"start": 0.02, "end": 4.31, "text": "Guten Tag ...",
     "speaker": "SPEAKER_00",
     "words": [
       {"word": "Guten", "start": 0.02, "end": 0.35,
        "score": 0.97, "speaker": "SPEAKER_00"}
     ]}
  ]
}
```

No mmt schema, no ids, no versions. The app's `normalize_content` performs the
conversion, exactly as it does for manually produced whisperX files today.

### `DELETE /jobs/{id}`

Cancels a queued job, or deletes a finished job and its artifacts (the job's
spool directory is removed). On a `running` job it sets `delete_requested`; the
worker removes the directory after the job finishes. Always `204` for known ids,
regardless of prior state.

### Job queue: spool directory

The queue is self-contained on purpose: no Redis, no Celery, no database server.
The service's queue state is a spool directory with one subdirectory per job:

```
spool/
  j_8f3ab2c1/
    job.json      # see field set below
    result.json   # whisperX output, present only when succeeded
```

The media file never enters the spool: the service reads it from shared storage
and does not delete it, because the app owns the media lifecycle.

- **Order is derived, not stored.** The worker scans the spool, filters
  `queued`, sorts by (`created_at`, `id`) and takes the first. There is no queue
  structure that could disagree with the job files.
- One **worker thread** in the uvicorn process loops: pick the oldest `queued`
  job, mark it `running`, transcribe, write `result.json`, mark it `succeeded`
  or `failed`. Concurrency is 1 by design: whisperX occupies the GPU fully and
  model memory is the limiting resource, so serializing jobs is the purpose of
  the service rather than a limitation of it.
- **Crash recovery.** On startup the service scans the spool; any job found
  `running` was interrupted mid-transcription and is reset to `queued`. Because
  the state lives on a volume, a container restart (out-of-memory kill, CUDA
  error, deployment) loses no jobs and the interrupted one runs again.

Celery and Redis inside the service were rejected because they would add three
additional components (broker, worker process, result backend) for a queue whose
depth is a handful of jobs, while the app-side Celery already provides retries
and scheduling on the caller side. An in-memory queue was rejected because jobs
represent hours of GPU time, so losing the queue on every deployment has a real
cost, while the spool costs one JSON file per job.

### `job.json`

Single source of truth for one job. Full field set:

```json
{
  "id": "j_8f3ab2c1",
  "status": "queued",
  "path": "user_files/abc/interview.mp4",
  "language": "de",
  "diarize": false,
  "progress": 0.0,
  "error": null,
  "delete_requested": false,
  "created_at": "2026-07-08T14:02:11+00:00",
  "started_at": null,
  "finished_at": null
}
```

Writes are atomic: write a temporary file in the job directory, then `os.replace`
it onto `job.json`.

### Transcription pipeline

Standard whisperX flow, with the model held as a module-level singleton like
[`ner/model.py`](../ner/model.py):

1. `whisperx.load_audio(path)` — ffmpeg decodes any container to 16 kHz mono;
   the service never inspects the media format itself.
2. `whisperx.load_model(MODEL, device, compute_type)`, then `transcribe`
   (faster-whisper backend, batched).
3. `whisperx.load_align_model(language)`, then `align`, for word-level
   timestamps. Alignment models are per language and cached under `HF_HOME`.
4. If `diarize`: pyannote pipeline (`whisperx.diarize.DiarizationPipeline`,
   a gated model requiring `HF_TOKEN`), then `assign_word_speakers`.

### Progress

The worker computes a single `[0, 1]` fraction from two levels:

- **Stage weights.** Fixed bands: transcribe `0.00–0.70`, align `0.70–0.95`,
  finalize `0.95–1.00`; with diarization `0.00–0.60`, `0.60–0.80`, `0.80–0.95`,
  `0.95–1.00`. Even with no signal within a stage, progress advances at every
  stage boundary.
- **Progress within a stage.** whisperx processes transcription and alignment as
  loops over VAD and text segments, but exposes progress only through
  `print_progress=True`, which prints `Progress: 34.52%...` per segment; there is
  no callback parameter. The worker captures this with
  `contextlib.redirect_stdout` into a line parser that maps each percentage into
  the current stage's band. This uses the public API only, and if whisperx
  changes the output format the parser matches nothing and progress advances at
  stage boundaries alone instead of raising an error.
- Progress never decreases: the job store clamps it to the maximum seen.

### Model weights and the Hugging Face cache

**Model weights are not included in the image.** `HF_HOME` points at
`/model_cache`, which is a named volume (`mmt-asr-models`) mounted read-write.
The build never contacts Hugging Face and `HF_TOKEN` is a runtime environment
variable, never a build secret.

Three reasons, in order of importance:

1. **Gated models must not be redistributed.** The diarization models
   `pyannote/speaker-diarization-3.1` and `pyannote/segmentation-3.0` are
   MIT-licensed but access-gated on Hugging Face: access requires accepting the
   model's conditions and providing contact details. Publishing them inside an
   image on a public registry would give the weights to anyone who pulls the
   image without them passing that gate. The license permits redistribution, but
   the gate exists so that the authors can record who obtained the weights, and
   this service does not circumvent it. This differs from the NER service, whose
   [`ner/Dockerfile`](../ner/Dockerfile) includes `fastino/gliner2-multi-v1`;
   that model is small and not gated, so the pattern does not transfer.
2. **Included weights are only used when build and runtime agree.**
   `WHISPERX_MODEL` is read from the environment at runtime by
   [`asr/config.py`](../asr/config.py), so a container configured for `small`
   ignores an included `large-v3` and downloads `small` on first use. The same
   applies to the alignment model of any language outside the included set.
3. **Image size.** whisper `large-v3` is roughly 3 GB and the German alignment
   model roughly 1.2 GB. Without them the image is dominated by torch and the
   `nvidia-*-cu12` wheels, which matters for the GitHub-hosted runner that builds
   it (roughly 14 GB of free disk) and for the Actions cache (10 GB per
   repository).

The cost of this decision is that the container needs network access to Hugging
Face the first time a given model is used, and that first job is slow by the
download time. `prefetch.py` exists to avoid that: it populates the volume ahead
of the first job.

```
podman run --rm \
       --volume mmt-asr-models:/model_cache \
       --env WHISPERX_MODEL=large-v3 \
       --env ALIGN_LANGUAGES="de en" \
       --env HF_TOKEN=... \
       ghcr.io/asr4memory/mmt-asr:TAG python prefetch.py
```

- It loads the whisper model and each alignment model on the CPU with
  `compute_type="int8"`, which is enough to populate the cache; the GPU is only
  used at runtime. The prefetch run therefore does not need `--device
  nvidia.com/gpu=all`.
- It downloads the diarization pipeline only when `HF_TOKEN` is set, so an
  installation that does not use diarization needs no token at all.
- It is idempotent: files already in the volume are not downloaded again, so the
  command is safe to repeat after a model change.

### Configuration

Both environments run CUDA; they differ only in model size:

| var | production | dev |
|---|---|---|
| `WHISPERX_MODEL` | `large-v3` | `small` (or `base`) |
| `WHISPERX_DEVICE` | `cuda` | `cuda` |
| `WHISPERX_COMPUTE_TYPE` | `float16` | `float16` (`int8_float16` if VRAM is tight) |
| `WHISPERX_BATCH_SIZE` | `16` | lower to fit VRAM |

Service-level settings:

| var | default | notes |
|---|---|---|
| `MEDIA_ROOT` | — | mount point of the shared media storage (read-only) |
| `SPOOL_DIR` | `./spool` | volume in production |
| `HF_HOME` | `/model_cache` | volume in production; set in the image |
| `RETENTION_DAYS` | `7` | |
| `HF_TOKEN` | — | diarization models only (slice 3), and `prefetch.py` |
| `ALIGN_LANGUAGES` | `de en` | read by `prefetch.py` only, not by the service |

Service-internal tuning (whisperX `chunk_size`, VAD options) stays constant in
[`asr/transcriber.py`](../asr/transcriber.py), like the NER service's
`WINDOW`/`OVERLAP`, and is not exposed per job.

### Deployment and CI

[`deploy/create-mmt-asr`](../deploy/create-mmt-asr) runs the container with:

- `--device nvidia.com/gpu=all` (NVIDIA container toolkit, CDI), which injects
  the host driver and `libcuda.so`.
- `--volume mmt-asr-spool:/spool` and `--volume mmt-asr-models:/model_cache`,
  both created if absent.
- `--volume "$MMT_MEDIA_ROOT:/media_root:ro"`.
- `WHISPERX_MODEL`, `WHISPERX_DEVICE`, `WHISPERX_COMPUTE_TYPE`,
  `WHISPERX_BATCH_SIZE` and `HF_TOKEN` forwarded from the caller's environment
  where set, so dev and production differ in configuration only. The service
  defaults in `config.py` apply when a variable is unset.

[`.github/workflows/asr-tests.yml`](../.github/workflows/asr-tests.yml) runs
`uv run pytest` from `asr/` on pushes to master and on pull requests, filtered to
`asr/**`. [`.github/workflows/asr-docker.yml`](../.github/workflows/asr-docker.yml)
builds and pushes the image **on `workflow_dispatch` only**, from whichever
branch is selected. It passes no build secrets. The build takes about 25
minutes because of the torch and CUDA wheels, and the service changes rarely,
so it does not run on every push to master; a new image is requested by hand
when one is needed. The consequence is that merging to master does not produce
an image, and a deployment must be preceded by a manual build.

Because a `workflow_dispatch` trigger is only offered for workflow files present
on the default branch, both ASR workflow files have to be on master before the
image can be built from `experimental/asr-service`.

### Decided conventions

- **Job id:** `"j_" + secrets.token_hex(4)`, for example `j_8f3ab2c1`. The spool
  directory is named by the id; on a collision, generate a new id.
- **Timestamps:** ISO 8601 UTC,
  `datetime.now(UTC).isoformat(timespec="seconds")`.
- **`error` string:** one line, `f"{type(exc).__name__}: {exc}"`.
- **Progress writes:** throttled, persisted only on a change of at least 0.01.
- **Retention:** jobs whose `finished_at` is older than `RETENTION_DAYS` are
  removed by a sweep in the worker loop, both `succeeded` and `failed`.
- **Worker idle poll:** sleep 1 s between spool scans when no job is queued.
- **Python 3.13**, not 3.14: whisperx requires `>=3.10,<3.14`.
- **whisperx is an optional extra** (`uv sync --extra whisperx`), not a default
  dependency: the tests replace it with a fake module, so neither local
  development nor CI downloads torch and the CUDA wheels. Only the image
  installs it.
- **The image is based on `python:3.13-slim`, not on a CUDA base image.**
  whisperx needs torch in any case (VAD, alignment, and later diarization), and
  the PyPI torch wheels contain their own CUDA runtime as `nvidia-*-cu12`
  dependencies; `uv.lock` pins cuBLAS, cuDNN 9 and the rest. The host driver and
  `libcuda.so` are injected by the NVIDIA container toolkit through CDI. A
  `nvidia/cuda:*-cudnn-runtime` base would therefore add a second, unused copy of
  cuDNN and cuBLAS (roughly 2.5 GB) and a second CUDA version to keep in sync
  with torch's. It would only be worthwhile with no torch in the image (plain
  faster-whisper), or if CUDA code had to be compiled at build time.
  Consequence: `LD_LIBRARY_PATH` must point at the wheels' library directories,
  because ctranslate2 opens cuDNN and cuBLAS with `dlopen` by soname and does not
  depend on those wheels itself.
- **Watch the cuDNN major version when relocking:** ctranslate2 4.5 and later
  require cuDNN 9. Since torch's `nvidia-cudnn-cu12` pin is the only copy in the
  image, a torch upgrade to a cuDNN 10 wheel would break transcription until
  ctranslate2 supports it.
- **`GET /jobs/{id}` always carries `error`** (null unless failed) rather than
  omitting the key, so callers parse one response shape.
- **`diarize: true` fails the job** with `NotImplementedError: diarization`
  until slice 3 lands, rather than returning output without speaker labels.
- **The result carries `language`:** whisperx's `align` output has no language
  key, so the transcriber adds the detected one. Everything else is passed
  through unchanged.

## File layout

Flat directory mirroring `ner/`, with tests beside sources:

```
asr/
  api.py           # FastAPI app, request/response models, path validation
  jobs.py          # job store: spool scan, state machine, atomic writes
  worker.py        # worker thread: pick loop, recovery, retention sweep
  transcriber.py   # the only module that imports whisperx at run time
  progress.py      # pure: line parser and stage-band mapping
  prefetch.py      # populates the HF_HOME volume; not imported by the service
  config.py        # env reading (MEDIA_ROOT, SPOOL_DIR, ...)
  test_api.py  test_jobs.py  test_worker.py  test_transcriber.py
  test_progress.py  test_prefetch.py
  pyproject.toml  Dockerfile  .dockerignore  README.md
```

Key signatures (the seams the tests replace):

```python
# jobs.py
def create_job(spool: Path, path: str, language: str | None, diarize: bool) -> dict
def load_job(spool: Path, job_id: str) -> dict | None
def update_job(spool: Path, job_id: str, **fields) -> dict   # atomic
def next_queued(spool: Path) -> dict | None                  # oldest first
def recover_interrupted(spool: Path) -> None                 # running -> queued
def sweep_expired(spool: Path, retention_days: int) -> None
def set_progress(spool: Path, job_id: str, progress: float) -> None  # monotonic, throttled
def delete_job(spool: Path, job_id: str) -> None
def list_jobs(spool: Path) -> list[dict]
def result_path(spool: Path, job_id: str) -> Path

# worker.py — transcribe is injected so tests never touch whisperx
class Worker:
    def __init__(self, spool: Path, transcribe: Transcribe,
                 idle_sleep: float = 1.0): ...
    def startup(self) -> None    # recover_interrupted + sweep_expired
    def run_once(self) -> bool   # run the oldest queued job, if any
    def start(self) -> None      # startup, then the thread
    def stop(self) -> None

# transcriber.py
Transcribe = Callable[[Path, str | None, bool, Callable[[float], None]], dict]
def transcribe(media: Path, language: str | None, diarize: bool,
               progress: Callable[[float], None]) -> dict

# progress.py
def parse_progress_line(line: str) -> float | None
def stage_fraction(stage: str, within: float, diarize: bool) -> float

# prefetch.py
def prefetch(model: str, languages: list[str], hf_token: str | None) -> None
def main() -> None    # reads WHISPERX_MODEL, ALIGN_LANGUAGES, HF_TOKEN

# config.py — env read on every call, so tests monkeypatch instead of reloading
def resolve_media(path: str) -> Path | None   # None if missing or outside MEDIA_ROOT
def align_languages() -> list[str]
def hf_token() -> str | None
```

## Tests

Run with `uv run pytest` from `asr/`; slice 4's tests run from `app/`.

whisperx is never installed in CI. `test_transcriber.py` and `test_prefetch.py`
insert a fake `whisperx` module into `sys.modules` and assert on the calls made
to it, so no model is downloaded and no GPU is required.

The tests of slices 1 and 2 are implemented: 85 tests, counted as pytest
collects them, so a parametrized function counts once per case.

### `test_progress.py` — parser and stage bands (18)

- **`test_parse_progress_line_reads_whisperx_output`** — parametrized over real
  whisperx samples: `Progress: 34.52%...`, the `0.00%` and `100.00%` ends, a
  percentage without decimals, and a line with surrounding whitespace and a
  trailing newline.
- **`test_parse_progress_line_ignores_anything_else`** — parametrized over an
  empty line, a bare newline, other whisperx output such as
  `Detected language: de`, a lower-case prefix, and a `Progress:` line without a
  parsable percentage; each returns `None`.
- **`test_bands_without_diarization`** — both edges of `transcribe`, `align` and
  `finalize` land exactly on `0.00–0.70`, `0.70–0.95`, `0.95–1.00`.
- **`test_bands_with_diarization`** — both edges of the four stages land exactly
  on `0.00–0.60`, `0.60–0.80`, `0.80–0.95`, `0.95–1.00`.
- **`test_within_maps_linearly_into_the_band`** — `within=0.5` maps to the
  midpoint of the stage's band.
- **`test_within_is_clamped`** — `within` outside `[0, 1]` yields the band's
  edges rather than leaving the band.
- **`test_diarize_stage_is_unavailable_without_diarization`** — `ValueError`.
- **`test_unknown_stage_raises`** — `ValueError`.

### `test_jobs.py` — job store (21)

- **`test_create_job_writes_the_full_field_set`** — the returned job equals the
  documented field set exactly, and `job.json` holds the same content.
- **`test_create_job_timestamps_in_utc_seconds`** — `created_at` parses as UTC
  with no sub-second component.
- **`test_create_job_ids_are_unique`** — 20 jobs produce 20 distinct ids.
- **`test_load_job_returns_none_for_unknown_id`**
- **`test_load_job_returns_none_for_a_traversing_id`** — an id containing `..`
  does not read outside the job directory.
- **`test_update_job_persists_a_status_transition`** — changed fields are
  written, unchanged fields are kept, and `job.json` matches the return value.
- **`test_update_job_writes_atomically_and_leaves_no_temp_files`** — `os.replace`
  is called with a temporary source onto `job.json`, and afterwards the job
  directory contains only `job.json`.
- **`test_update_job_on_unknown_id_raises`** — `KeyError`.
- **`test_next_queued_takes_the_oldest_job`** — ordering by `created_at`.
- **`test_next_queued_breaks_ties_by_id`** — equal `created_at` resolves to the
  smaller id.
- **`test_next_queued_ignores_jobs_that_are_not_queued`**
- **`test_next_queued_on_an_empty_spool`** — returns `None`, and the spool
  directory does not have to exist.
- **`test_recover_interrupted_resets_running_jobs_and_nothing_else`** — a
  `running` job becomes `queued` with `started_at` and `progress` unchanged;
  `queued` and `succeeded` jobs are untouched.
- **`test_sweep_expired_removes_finished_jobs_past_retention`** — `succeeded`
  and `failed` jobs past retention are removed, a recently finished job and a
  `queued` job are kept.
- **`test_sweep_expired_keeps_a_long_running_job`** — a job started 30 days ago
  and still `running` is not removed, because retention reads `finished_at`.
- **`test_delete_job_removes_the_spool_directory`**
- **`test_set_progress_persists_a_change_of_at_least_one_percent`**
- **`test_set_progress_throttles_smaller_changes`** — a change below 0.01 is not
  written.
- **`test_set_progress_never_moves_backwards`** — a lower value keeps the
  maximum seen.
- **`test_set_progress_clamps_to_the_unit_interval`** — `1.5` is stored as `1.0`.
- **`test_set_progress_on_a_deleted_job_is_a_no_op`** — no directory is
  recreated and no error is raised.

### `test_worker.py` — worker loop (12)

The transcriber is injected, so no test touches whisperx.

- **`test_run_once_without_a_queued_job_does_nothing`** — returns `False`.
- **`test_a_queued_job_succeeds_and_writes_its_result`** — status `succeeded`,
  `progress` 1.0, no error, `started_at` and `finished_at` set, and
  `result.json` holds the transcriber's output.
- **`test_the_running_job_is_marked_running_and_gets_the_media_path`** — the
  transcriber sees the absolute path under `MEDIA_ROOT`, the job's `language` and
  `diarize`, and the job is `running` while it executes.
- **`test_progress_callback_lands_in_the_job_file`** — a value passed to the
  callback is readable from `job.json` during the run, and the job ends at 1.0.
- **`test_a_failing_transcriber_marks_the_job_failed`** — status `failed`,
  `error` in the decided format, `finished_at` set, no `result.json`.
- **`test_media_deleted_while_queued_fails_the_job`** — `FileNotFoundError` in
  the error string.
- **`test_media_escaping_the_root_fails_the_job`** — a `..` path stored in a job
  fails at run time even though the file exists outside the root.
- **`test_delete_requested_during_a_run_removes_the_job_after_it_finishes`**
- **`test_delete_requested_removes_a_failed_job_too`**
- **`test_run_once_takes_the_oldest_job`** — the newer job stays `queued`.
- **`test_the_thread_drains_the_queue_and_stops`** — `start` runs the queued job
  and `stop` ends the thread.
- **`test_startup_recovers_interrupted_jobs_and_sweeps`** — an interrupted
  `running` job is reset to `queued` and an expired job is removed.

### `test_api.py` — HTTP contract (20)

`MEDIA_ROOT` and `SPOOL_DIR` point at `tmp_path` and the worker is replaced by a
no-op, so the tests drive job state directly.

- **`test_post_jobs_creates_a_queued_job`** — `202`, status `queued`, and the
  spooled job carries the submitted path and language.
- **`test_post_jobs_defaults_language_and_diarize`** — `None` and `False`.
- **`test_post_jobs_accepts_diarize`**
- **`test_post_jobs_rejects_a_path_missing_on_disk`** — `400` and no job is
  created.
- **`test_post_jobs_rejects_a_path_escaping_the_media_root`** — `400` for a
  leading `..` and for a `..` in the middle of the path.
- **`test_post_jobs_rejects_an_absolute_path`** — `400`.
- **`test_post_jobs_rejects_a_directory`** — `400`.
- **`test_post_jobs_rejects_a_malformed_body`** — `422` for a missing `path` and
  for a non-boolean `diarize`.
- **`test_get_job_returns_the_status_object`** — the response equals the
  documented field set exactly.
- **`test_get_job_reports_the_error_of_a_failed_job`**
- **`test_get_job_unknown_id`** — `404`.
- **`test_get_result_returns_the_whisperx_output_as_is`** — the stored
  `result.json` is returned unchanged.
- **`test_get_result_unknown_id`** — `404`.
- **`test_get_result_before_success_is_a_conflict`** — parametrized over
  `queued`, `running` and `failed`; each is `409`.
- **`test_delete_removes_a_queued_job`** — `204`, job gone.
- **`test_delete_removes_a_finished_job_and_its_artifacts`** — `204`, spool
  directory including `result.json` gone.
- **`test_delete_only_marks_a_running_job`** — `204`, status stays `running`,
  `delete_requested` becomes `true`.
- **`test_delete_unknown_id`** — `404`.

### `test_transcriber.py` — whisperx wiring (9)

- **`test_the_media_path_is_decoded_by_whisperx`** — `load_audio` receives the
  path as a string.
- **`test_the_model_is_loaded_from_the_environment_and_cached`** — `load_model`
  is called once across two transcriptions, with the model, device and compute
  type from the environment.
- **`test_an_explicit_language_is_passed_through`** — together with
  `WHISPERX_BATCH_SIZE`.
- **`test_an_omitted_language_is_left_to_auto_detection`** — `language=None`
  reaches `transcribe`, and the detected language is used for the alignment
  model and reported in the result.
- **`test_the_aligned_output_is_returned_unmodified`** — the align output plus
  the added `language` key, nothing else.
- **`test_the_transcribed_segments_are_handed_to_align`** — segments, alignment
  model, metadata and decoded audio, in that order.
- **`test_progress_moves_through_the_stage_bands_in_order`** — the captured
  `Progress:` lines map into the transcribe and align bands, and the sequence of
  callback values does not decrease.
- **`test_whisperx_progress_output_is_not_printed`** — the redirected stdout does
  not reach the service's own output.
- **`test_diarization_is_not_supported_yet`** — `NotImplementedError`.

### `test_prefetch.py` — cache population (5)

- **`test_prefetch_loads_the_configured_model_on_the_cpu`** — `prefetch` calls
  `whisperx.load_model` with the given model name, `"cpu"` and
  `compute_type="int8"`, so no GPU is required.
- **`test_prefetch_loads_an_align_model_per_language`** — one
  `load_align_model(language_code=..., device="cpu")` call per entry of the
  language list, in order.
- **`test_prefetch_skips_diarization_without_a_token`** — with `hf_token=None`,
  no diarization pipeline is constructed.
- **`test_prefetch_loads_the_diarization_pipeline_with_a_token`** — with a
  token, `DiarizationPipeline` is constructed with it.
- **`test_main_reads_the_environment`** — `main` passes `WHISPERX_MODEL`, the
  whitespace-separated `ALIGN_LANGUAGES` and `HF_TOKEN` through to `prefetch`,
  and applies the documented defaults when they are unset.

The tests of the remaining slices are not implemented yet.

### Slice 3 — diarization

- **`test_diarization_assigns_speakers_to_words`** — with `diarize=True` the
  transcriber runs the pyannote pipeline and passes its output to
  `assign_word_speakers`, returning the result of that call.
- **`test_diarization_progress_uses_the_diarize_bands`** — the progress
  callbacks follow `0.00–0.60`, `0.60–0.80`, `0.80–0.95`, `0.95–1.00`.
- **`test_diarization_without_a_token_fails_the_job`** — with `HF_TOKEN` unset,
  the transcriber raises and the worker marks the job `failed` with the decided
  error format.
- The existing `test_diarization_is_not_supported_yet` in `test_transcriber.py`
  is removed by this slice, since it asserts the placeholder behavior.

### Slice 4 — app integration

- **`test_submit_posts_the_relative_path_and_stores_the_job_id`** — the submit
  task posts the file's storage-relative path and marks the job `submitted`.
- **`test_sweep_copies_progress_and_timestamps`** — a `running` service response
  updates `progress`, `started_at` and `finished_at` on the model.
- **`test_sweep_ingests_a_succeeded_job`** — the result is fetched, run through
  `normalize_content` and `validate_mmt_content`, and a `Transcript` is created
  and linked.
- **`test_sweep_records_a_failed_job`** — the service's `error` is stored and
  the job becomes `failed`.
- **`test_sweep_resubmits_once_on_404`** — a `404` resubmits, and a second `404`
  marks the job `failed`.
- **`test_sweep_leaves_terminal_jobs_untouched`** — a `succeeded` or `failed`
  job is not queried again by a later sweep.
- **`test_transcribe_action_requires_the_transcribers_group`** — a non-member
  receives `403` and does not see the action.

## Slices and tasks

Each slice leaves the system working and independently deployable. Each task is
one session.

### Slice 1 — service skeleton with fake transcriber

Full queue and HTTP contract, with `transcribe` as a stub. Deployable because
nothing calls it yet.

- [x] (2026-07-08) **1.1 Scaffold.** `asr/` uv project (fastapi, uvicorn; dev:
  pytest, httpx), empty `api.py` serving. Done when `uv run pytest` runs (zero
  tests) and `uv run uvicorn api:app` starts.
- [x] (2026-07-08) **1.2 `progress.py`.** Parser and `stage_fraction`, pure.
  Done when `test_progress.py` covers: real whisperx `Progress: NN.NN%...`
  samples, unparseable lines returning `None`, band mapping with and without
  diarization, band edges landing exactly on the decided boundaries.
- [x] (2026-07-08) **1.3 `jobs.py`.** Store per the signatures above. Done when
  `test_jobs.py` covers: create writes `job.json` matching the field set; status
  transitions; atomic write (temp file plus `os.replace`); `next_queued` order
  (`created_at`, then `id`); `recover_interrupted` resets `running` to `queued`
  and changes nothing else; `sweep_expired` removes only finished jobs past
  retention; progress clamped, monotonic and throttled at 0.01.
- [x] (2026-07-08) **1.4 `worker.py`.** Thread with injected `transcribe`. Done
  when `test_worker.py` covers: queued job becomes `running` then `succeeded`
  with `result.json` written; transcriber exception becomes `failed` with the
  decided `error` format; the progress callback reaches `job.json`;
  `delete_requested` honored after the run finishes; media file missing at run
  time becomes `failed`.
- [x] (2026-07-08) **1.5 `api.py`.** Full contract wired to `jobs.py`, worker
  started on app startup, fake transcriber injectable. Done when `test_api.py`
  (TestClient, `MEDIA_ROOT` and `SPOOL_DIR` pointing at `tmp_path`) covers every
  row of the endpoint table, including `400` on a missing file and on a `..`
  path, `409` on requesting a result before success, and the `DELETE` semantics
  per state.

### Slice 2 — real transcription

- [x] (2026-07-08) **2.1 `transcriber.py`.** whisperx wiring (transcribe and
  align, no diarization), module-level model singleton, stdout capture feeding
  `progress.py`. Done when `test_transcriber.py` (whisperx replaced by a fake
  module) covers: language passthrough versus auto-detection, stage progress
  calls in band order, output returned unmodified. No model download in CI.
- [x] (2026-07-08) **2.2 Dockerfile.** NER pattern: uv-locked build stage,
  `ffmpeg` in the runtime stage, non-root user, port-8000 healthcheck. Done when
  the image builds and serves `/docs` locally. (2026-07-08: written and reviewed
  but not built, because there was no GPU host and no build in that session.
  `/docs`, path validation, the queue and the `failed` path were verified against
  a stub whisperx module instead. 2026-07-21: the model download stage this task
  added is superseded by task 2.3; the image has still never been built.)
- [x] (2026-07-21) **2.3 Model cache volume and prefetch.** Remove the weight download stage
  and the `WHISPERX_MODEL` and `ALIGN_LANGUAGES` build arguments from the
  Dockerfile, keeping `HF_HOME=/model_cache` and declaring it a volume. Add
  `prefetch.py` and the `align_languages` and `hf_token` readers in `config.py`.
  Done when `test_prefetch.py` passes and the Dockerfile contains no reference to
  Hugging Face downloads or `HF_TOKEN`.
- [ ] **2.4 Deploy and CI.** [`deploy/create-mmt-asr`](../deploy/create-mmt-asr):
  add the `mmt-asr-models` volume and the forwarded `WHISPERX_*` and `HF_TOKEN`
  variables alongside the existing spool volume, read-only media volume and CDI
  GPU device. Put both ASR workflow files on master so that
  `workflow_dispatch` is offered, then build the image from the branch. Done when
  "ASR Tests" is green on a pull request and "ASR Docker image" has pushed a tag
  built from `experimental/asr-service`.
  (2026-07-21: the deploy script is written, and the image built and pushed from
  the branch on the first attempt, so the runner's disk was sufficient without
  the model weights. The "ASR Tests" run on a pull request is still outstanding.
  The image has not been run anywhere yet: the development machine has no GPU and
  no podman, so every check that needs the running container belongs to task
  2.5.)
- [x] **2.5 Smoke test.** On the dev GPU machine: run `prefetch.py` against a
  fresh `mmt-asr-models` volume with a small model, start the container, submit a
  roughly 30 s fixture file, watch `progress` move through both bands, and expect
  `succeeded` with non-empty word-level segments. Record the result in this doc.
  This is also the first run that exercises the GPU at all: confirm
  `torch.cuda.is_available()` inside the container, and that ctranslate2 loads
  cuDNN through `LD_LIBRARY_PATH` (a failure appears as "Unable to load
  libcudnn_ops.so.9" on the first `load_model`). Note that `nvidia-smi` is not in
  the image.

  (2026-07-23: verified in CPU mode. `prefetch.py`, container start, fixture
  submission, `progress` moving through both bands, and a `succeeded` result with
  non-empty word-level segments all pass. The GPU path is still unverified:
  `torch.cuda.is_available()` and the ctranslate2 cuDNN load through
  `LD_LIBRARY_PATH` have not been exercised because the dev machine has no GPU.)

### Slice 3 — diarization

- [ ] **3.1 End-to-end `diarize`.** pyannote pipeline in `transcriber.py`,
  reading `HF_TOKEN` from the environment at run time, with the diarization stage
  band active. The models are downloaded by `prefetch.py` into the model volume
  and are never included in the image (see
  [Model weights and the Hugging Face cache](#model-weights-and-the-hugging-face-cache)).
  Extend `prefetch.py` if the pipeline needs more than the pipeline constructor
  to populate the cache. Done when the slice 3 tests above pass and a dev smoke
  run shows `speaker` fields in the result.

### Slice 4 — app integration

Last slice, and only after the service contract has been exercised by real use
(task 2.5 at minimum).

Transcription jobs are **fully decoupled from `ProcessingRequest`**. That model
is a human workflow ticket (admin review, a list of files, four possible
actions); a `TranscriptionJob` is machine execution state for exactly one media
file. No foreign key, no fan-out on accept, no shared status vocabulary. If the
ticket workflow is ever to create jobs, that is a separate later decision and
nothing in this slice anticipates it.

Polling design: **one beat-scheduled sweep, not per-job retry chains.** A per-job
`self.retry(countdown=30)` chain does not occupy a worker (it re-enqueues with an
ETA), but 20 concurrent jobs would mean 20 long-lived chains whose only state is
broker messages. Those need `max_retries=None`, stop without a record if the
broker drops a message, and offer no single place to see what is pending. The
sweep runs a constant number of tasks regardless of how many jobs exist, keeps
pending state in the database so that a missed tick is corrected by the next one,
and is straightforward to inspect. Never poll by sleeping inside a task body,
which does occupy a worker slot.

- [ ] **4.1 `TranscriptionJob` model and settings.** FK to `UploadedFile`,
  nullable FK to the produced `Transcript`, `asr_job_id`, status
  (`pending | submitted | running | succeeded | failed`), `progress`, `error`,
  `language`, `diarize`; timestamps: `created_at` and `updated_at` as standard
  auto columns (`updated_at` doubles as "last heard from the service", because
  the sweep touches every non-terminal job), plus nullable `started_at` and
  `finished_at` copied from the service's status response. The service owns
  execution time; the app never records its own observation times. No
  `submitted_at`, because `asr_job_id IS NOT NULL` encodes it. `MMT_ASR_API_URL`
  env setting beside `MMT_NER_API_URL`. Done when model and admin tests pass.
- [ ] **4.2 Submit task and sweep poller.** `submit_transcription_job(id)` posts
  the file's storage-relative path, stores the ASR job id and marks the job
  `submitted`. A beat-scheduled sweep (every 60 s) queries non-terminal jobs and
  GETs each: it copies `progress`, `started_at` and `finished_at`; on `succeeded`
  it fetches the result, runs `normalize_content` and `validate_mmt_content` (the
  identical path a manual whisperX upload takes), creates the `Transcript`, links
  it and marks the job `succeeded`; on `failed` it stores the error; on `404`
  (service data loss) it resubmits once and then records an error. Done when the
  slice 4 tests above pass.
- [ ] **4.3 Beat in deployment.** Celery beat added to the deployment, either as
  its own compose service or as `-B` on the worker while there is exactly one
  worker container. Beat is expected to serve future periodic tasks as well, not
  only this sweep. Done when compose brings up beat and the sweep runs in a dev
  run.
- [ ] **4.4 Trigger and UI.** A "Transcribe" action on an uploaded file,
  available only to members of the "Transcribers" group, creates and submits a
  `TranscriptionJob`. The file's page shows job status, progress and errors, and
  links the resulting transcript. Done when the trigger flow test passes,
  including a non-member receiving `403` and not seeing the action, and the
  template shows the job state.

## Assumptions

- The shared media storage is mountable as a regular filesystem on the service
  host, because whisperx and ffmpeg read from a local path.
- Production is a CUDA GPU host sized for `large-v3`; dev has CUDA with a smaller
  model. Only the environment configuration differs between the two.
- The service host has outbound network access to Hugging Face at least once per
  model, for the prefetch run.
