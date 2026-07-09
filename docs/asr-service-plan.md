# Plan: ASR service

Status: not started.

This document is an **executable spec** (spec-driven development): it is
the prompt an implementing session works from and the authoritative record
of every decision, not a background sketch. Execute it slice by slice, one
task per session. Check off tasks (`[x]`, with date) as they land and keep
the "Decided" sections authoritative: an implementing session resolves
ambiguity by reading this doc, not by inventing; if a genuinely new
decision comes up, write it into the doc as part of the task.

## Motivation

Transcription is currently a manual step: a user files a
`ProcessingRequest`, an admin runs whisperX by hand and uploads the result.
A transcription service closes that loop the same way the NER service did
for entity extraction: a small, self-contained FastAPI capability — media
in, transcript out — that the app drives from Celery.

Like the NER service, the ASR service is **format-agnostic**. It
returns whisperX's native output and knows nothing about the
mmt-transcript format. The app already converts lenient Whisper/whisperX
JSON into mmt content (`normalize_content` in
`mmt/transcripts/normalize.py`), so the service output plugs straight into
the existing ingest path.

The one structural difference from NER: transcription of an hour of media
takes minutes to hours, far beyond a sane HTTP request lifetime, and the
model must process jobs serially (one GPU / one model instance). So the
service is asynchronous around a **job queue**: submit, poll, fetch result.

## Non-goals (v1)

Do not add these, even where they would be easy:

- **No auth.** Private network, same as the NER service.
- **No webhooks/callbacks.** The app polls; the service never initiates
  connections.
- **No cancellation of running jobs.** `DELETE` on a running job only marks
  it for cleanup after it finishes.
- **No priorities or reordering.** Strict FIFO by submission time.
- **No file upload endpoint.** Media is referenced by path on shared
  storage only.
- **No mmt-transcript knowledge.** The service never sees or produces mmt
  format, ids, or versions.
- **No concurrency.** One worker thread, one job at a time, `--workers 1`.
- **No result archive.** Retention is a safety margin for slow pollers,
  not storage.

## Service reference

### Endpoints

| method & path | success | errors |
|---|---|---|
| `POST /jobs` | `202` job created | `400` path missing on disk or escapes `MEDIA_ROOT`; `422` malformed body (FastAPI default) |
| `GET /jobs/{id}` | `200` status object | `404` unknown id |
| `GET /jobs/{id}/result` | `200` whisperX JSON | `404` unknown id; `409` job not `succeeded` |
| `DELETE /jobs/{id}` | `204` | `404` unknown id |

Unknown ids are `404` also after service data loss; callers treat 404 as
"gone, resubmit".

### `POST /jobs`

JSON body referencing the media file on shared storage — the media volume
is reachable by all systems, so no bytes cross the wire.

```json
{"path": "user_files/abc/interview.mp4", "language": "de", "diarize": false}
```

| field | type | notes |
|---|---|---|
| `path` | string | relative to `MEDIA_ROOT`; any format ffmpeg can read |
| `language` | string, optional | ISO 639-1; omitted → whisper auto-detect |
| `diarize` | bool, default `false` | speaker diarization (slice 3) |

The path is resolved against `MEDIA_ROOT` and must stay inside it; a file
that doesn't exist at submit time is rejected, so bad paths fail fast
instead of in the queue. The worker re-checks at run time — the file could
be deleted while queued — and marks the job `failed` if it's gone.

Response `202`:

```json
{"id": "j_8f3ab2c1", "status": "queued"}
```

### `GET /jobs/{id}`

```json
{"id": "j_8f3ab2c1", "status": "running", "progress": 0.65,
 "created_at": "2026-07-08T14:02:11+00:00",
 "started_at": "2026-07-08T14:05:03+00:00", "finished_at": null,
 "language": "de"}
```

`status` is one of `queued | running | failed | succeeded`. `progress` is
a fraction in `[0, 1]`: `0` while queued, monotonically increasing while
running, `1` when succeeded. Failed jobs carry an `error` string.
`started_at` and `finished_at` come straight from `job.json` (null until
reached) — callers copy them rather than timestamping their own
observations, which would only be as precise as their polling interval.

### `GET /jobs/{id}/result`

Only valid for `succeeded` jobs (`409` otherwise). Returns whisperX's
aligned output as-is:

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

No mmt schema, no ids, no versions — the app's `normalize_content` owns
the conversion, exactly as it does for manually produced whisperX files
today.

### `DELETE /jobs/{id}`

Cancels a queued job, or deletes a finished job and its artifacts (the
job's spool directory is removed). On a `running` job it sets
`delete_requested`; the worker removes the directory after the job
finishes. Always `204` for known ids, regardless of prior state.

### Decided conventions

- **Job id:** `"j_" + secrets.token_hex(4)` (e.g. `j_8f3ab2c1`). The spool
  directory is named by the id; on the (unlikely) collision, generate a
  new id.
- **Timestamps:** ISO 8601 UTC,
  `datetime.now(UTC).isoformat(timespec="seconds")`.
- **`error` string:** one line, `f"{type(exc).__name__}: {exc}"`.
- **Progress writes:** throttled — persist only on a change of ≥ 0.01.
- **Retention:** jobs whose `finished_at` is older than `RETENTION_DAYS`
  are removed by a sweep in the worker loop (both `succeeded` and
  `failed`).
- **Worker idle poll:** sleep 1 s between spool scans when no job is
  queued.

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

Writes are atomic: write a temp file in the job directory, `os.replace`
onto `job.json`.

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
| `RETENTION_DAYS` | `7` | |
| `HF_TOKEN` | — | only needed for diarization models (slice 3) |

Service-internal tuning (whisperX `chunk_size`, VAD options) stays
constant in `transcriber.py`, like the NER service's `WINDOW`/`OVERLAP` —
not exposed per job.

## Design

### Job queue: spool directory

Self-contained on purpose — no Redis, no Celery, no database server. The
service's queue state is a spool directory, one subdirectory per job:

```
spool/
  j_8f3ab2c1/
    job.json      # see field set above
    result.json   # whisperX output (present iff succeeded)
```

The media file never enters the spool: the service reads it from shared
storage and does not delete it — the app owns the media lifecycle.

- **Order is derived, not stored:** the worker scans the spool, filters
  `queued`, sorts by (`created_at`, `id`), takes the first. No queue
  structure exists that could disagree with the job files.
- One **worker thread** in the uvicorn process loops: pick the oldest
  `queued` job, mark `running`, transcribe, write `result.json`, mark
  `succeeded`/`failed`. Concurrency is 1 by design — whisperX saturates
  the GPU and model memory is the bottleneck; queueing *is* the feature.
- **Crash recovery:** on startup, scan the spool; any job found `running`
  was interrupted mid-transcription and is reset to `queued`. Because
  state lives on a volume, a container restart (OOM, CUDA error, deploy)
  loses no jobs — the interrupted one simply runs again.

Why not Celery/Redis inside the service: it would triple the moving parts
for a queue whose depth is a handful of jobs, and the app-side Celery
already provides retries and scheduling on the caller side. Why not
in-memory only: jobs are hours of GPU time; losing the queue on every
deploy is a real cost, and the spool costs one JSON file per job.

### Transcription pipeline

Standard whisperX flow, model held as a module-level singleton like
`ner/model.py`:

1. `whisperx.load_audio(path)` — ffmpeg decodes any container to 16 kHz
   mono; the service never inspects the media format itself.
2. `whisperx.load_model(MODEL, device, compute_type)` → `transcribe`
   (faster-whisper backend, batched).
3. `whisperx.load_align_model(language)` → `align` for word-level
   timestamps. Align models are per-language and cached under `HF_HOME`.
4. If `diarize`: pyannote pipeline (`whisperx.diarize.DiarizationPipeline`,
   gated model, needs `HF_TOKEN`) → `assign_word_speakers`.

### Progress

The worker computes a single `[0, 1]` fraction from two levels:

- **Stage weights.** Fixed bands: transcribe `0.00–0.70`, align
  `0.70–0.95`, finalize `0.95–1.00`; with diarization `0.00–0.60` /
  `0.60–0.80` / `0.80–0.95` / `0.95–1.00`. Even with no intra-stage
  signal, progress moves at every stage boundary.
- **Intra-stage progress.** whisperx processes transcription and alignment
  as loops over VAD/text segments but exposes progress only via
  `print_progress=True` (it prints `Progress: 34.52%...` per segment;
  there is no callback parameter). The worker captures this with
  `contextlib.redirect_stdout` into a line parser that maps each
  percentage into the current stage's band. Least invasive option — public
  API only — and it degrades gracefully: if whisperx changes the format,
  parsing finds nothing and progress sticks to stage boundaries instead of
  breaking.
- Progress never moves backwards: the job store clamps to the maximum
  seen.

## File layout

Flat directory mirroring `ner/`, tests beside sources:

```
asr/
  api.py           # FastAPI app, request/response models, path validation
  jobs.py          # job store: spool scan, state machine, atomic writes
  worker.py        # worker thread: pick loop, recovery, retention sweep
  transcriber.py   # the only module that imports whisperx
  progress.py      # pure: line parser + stage-band mapping
  config.py        # env reading (MEDIA_ROOT, SPOOL_DIR, ...)
  test_api.py  test_jobs.py  test_worker.py  test_transcriber.py  test_progress.py
  pyproject.toml  Dockerfile  README.md
```

Key signatures (the seams the tests fake):

```python
# jobs.py
def create_job(spool: Path, path: str, language: str | None, diarize: bool) -> dict
def load_job(spool: Path, job_id: str) -> dict | None
def update_job(spool: Path, job_id: str, **fields) -> dict   # atomic
def next_queued(spool: Path) -> dict | None                  # oldest first
def recover_interrupted(spool: Path) -> None                 # running -> queued
def sweep_expired(spool: Path, retention_days: int) -> None

# worker.py — transcribe injected so tests never touch whisperx
class Worker:
    def __init__(self, spool: Path, transcribe: Transcribe): ...

# transcriber.py
Transcribe = Callable[[Path, str | None, bool, Callable[[float], None]], dict]
def transcribe(media: Path, language: str | None, diarize: bool,
               progress: Callable[[float], None]) -> dict

# progress.py
def parse_progress_line(line: str) -> float | None
def stage_fraction(stage: str, within: float, diarize: bool) -> float
```

## Slices and tasks

Each slice leaves the system working and independently deployable. Each
task is one session: tests first, done when its named checks pass via
`uv run pytest` from `asr/` (slice 4: from `app/`).

### Slice 1 — service skeleton with fake transcriber

Full queue + HTTP contract, `transcribe` is a stub. Deployable: nothing
calls it yet.

- [ ] **1.1 Scaffold.** `asr/` uv project (fastapi, uvicorn; dev:
  pytest, httpx), empty `api.py` serving. Done when `uv run pytest`
  runs (zero tests) and `uv run uvicorn api:app` starts.
- [ ] **1.2 `progress.py`.** Parser + `stage_fraction`, pure. Done when
  `test_progress.py` covers: real whisperx `Progress: NN.NN%...` samples,
  garbage lines → `None`, band mapping with and without diarization,
  band edges land exactly on the decided boundaries.
- [ ] **1.3 `jobs.py`.** Store per the signatures above. Done when
  `test_jobs.py` covers: create → `job.json` matches the field set;
  status transitions; atomic write (temp + `os.replace`); `next_queued`
  order (`created_at`, then `id`); `recover_interrupted` resets `running`
  → `queued` and nothing else; `sweep_expired` removes only finished jobs
  past retention; progress clamped monotonic and throttled at 0.01.
- [ ] **1.4 `worker.py`.** Thread with injected `transcribe`. Done when
  `test_worker.py` covers: queued job → `running` → `succeeded` with
  `result.json` written; transcriber exception → `failed` with the decided
  `error` format; progress callback lands in `job.json`;
  `delete_requested` honored after finish; media file missing at run time
  → `failed`.
- [ ] **1.5 `api.py`.** Full contract wired to `jobs.py`, worker started
  on app startup, fake transcriber injectable. Done when `test_api.py`
  (TestClient, `MEDIA_ROOT`/`SPOOL_DIR` → `tmp_path`) covers every row of
  the endpoint table, including `400` on missing file and on `..` escape,
  `409` on result-before-succeeded, and `DELETE` semantics per state.

### Slice 2 — real transcription

- [ ] **2.1 `transcriber.py`.** whisperx wiring (transcribe + align, no
  diarization), module-level model singleton, stdout capture feeding
  `progress.py`. Done when `test_transcriber.py` (whisperx mocked as a
  module) covers: language passthrough vs. auto-detect, stage progress
  calls in band order, output returned unmodified. No model download in
  CI.
- [ ] **2.2 Dockerfile.** NER pattern: uv-locked build stage, model
  weights pre-downloaded (`HF_HOME=/model_cache`), `ffmpeg` in the runtime
  stage, non-root user, port-8000 healthcheck. Done when the image builds
  and serves `/docs` locally.
- [ ] **2.3 Deploy + CI.** `deploy/create-mmt-asr` (spool volume,
  media volume read-only, GPU via CDI `--device nvidia.com/gpu=all`);
  `asr-tests.yml` and `asr-docker.yml` workflows mirroring the NER
  ones. Done when CI is green on a branch push touching `asr/`.
- [ ] **2.4 Smoke test.** On the dev GPU machine: submit a ~30 s fixture
  file, watch `progress` move through both bands, expect `succeeded` with
  non-empty word-level segments. Record the result in this doc.

### Slice 3 — diarization

- [ ] **3.1 End-to-end `diarize`.** pyannote pipeline in
  `transcriber.py`, models pre-downloaded in the image (`HF_TOKEN` build
  secret like NER's), diarization stage band active. Done when
  mocked-module tests cover the diarization branch and a dev smoke run
  shows `speaker` fields in the result.

### Slice 4 — app integration

Last slice, only after the service contract has survived real use
(slice 2's smoke test at minimum).

Transcription jobs are **fully decoupled from `ProcessingRequest`**. That
model is a human workflow ticket (admin review, a list of files, four
possible actions); a `TranscriptionJob` is machine execution state for
exactly one media file. No foreign key, no fan-out on accept, no shared
status vocabulary — if the ticket workflow ever wants to spawn jobs,
that's a separate later decision, and nothing in this slice should
anticipate it.

Polling design: **one beat-scheduled sweep, not per-job retry chains.** A
per-job `self.retry(countdown=30)` chain doesn't block workers (it
re-enqueues with an ETA), but 20 concurrent jobs would mean 20 long-lived
chains whose only state is broker messages — needing `max_retries=None`,
dying silently if the broker drops one, and offering no single place to
see what's pending. The sweep is O(1) tasks regardless of how many jobs
exist, keeps pending state in the database (a lost tick self-heals on the
next), and is trivially observable. Never poll by sleeping inside a task
body — that *does* occupy a worker slot.

- [ ] **4.1 `TranscriptionJob` model + settings.** FK to `UploadedFile`,
  nullable FK to the produced `Transcript`, `asr_job_id`, status
  (`pending | submitted | running | succeeded | failed`), `progress`,
  `error`, `language`, `diarize`; timestamps: `created_at`/`updated_at`
  as standard auto columns (`updated_at` doubles as "last heard from the
  service" since the sweep touches every non-terminal job), plus nullable
  `started_at`/`finished_at` copied from the service's status response —
  the service owns execution time; the app never stamps its own
  observations. No `submitted_at`: `asr_job_id IS NOT NULL` encodes
  it. `MMT_ASR_API_URL` env setting beside `MMT_NER_API_URL`. Done
  when model + admin tests pass.
- [ ] **4.2 Submit task + sweep poller.** `submit_transcription_job(id)`
  posts the file's storage-relative path, stores the ASR job id,
  marks the job `submitted`. A beat-scheduled sweep (every 60 s) queries
  non-terminal jobs and GETs each: copies `progress`, `started_at`, and
  `finished_at`; on `succeeded`
  fetches the result, runs `normalize_content` + `validate_mmt_content`
  (the identical path a manual whisperX upload takes), creates the
  `Transcript`, links it, marks the job `succeeded`; on `failed` stores
  the error; on `404` (service data loss) resubmits once, then errors.
  Done when task tests with mocked HTTP cover submit, a sweep over mixed
  statuses (running/succeeded/failed/404), and a terminal job surviving a
  re-sweep unchanged.
- [ ] **4.3 Beat in deployment.** Celery beat added to the deployment —
  its own compose service, or `-B` on the worker while there is exactly
  one worker container. Beat is expected to serve future periodic tasks
  too, not just this sweep. Done when compose brings up beat and the
  sweep fires in a dev run.
- [ ] **4.4 Trigger + UI.** A "Transcribe" action on an uploaded file
  (only available to members of the "Transcribers" group) creates and
  submits a `TranscriptionJob`; the file's
  page shows job status, progress, and errors, and links the resulting
  transcript. Done when the trigger flow test passes (including a
  non-member getting 403 and not seeing the action) and the template
  shows the job state.

## Assumptions

- The shared media storage is mountable as a regular filesystem on the
  service host (whisperx/ffmpeg need a local path to read from).
- Production is a CUDA GPU host sized for `large-v3`; dev has CUDA with a
  smaller model. Only env configuration differs between the two.
