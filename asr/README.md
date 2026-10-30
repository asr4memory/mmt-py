# ASR Service

Automatic speech recognition microservice based on
[whisperX](https://github.com/m-bain/whisperX).

The service is format-agnostic: it knows nothing about the mmt transcript
format and returns whisperX's aligned output as-is. Transcription takes
minutes to hours and the model runs one job at a time, so the service is
asynchronous around a job queue: submit, poll, fetch result.

Media is referenced by a path on shared storage, relative to `MEDIA_ROOT` —
no bytes cross the wire.

| method & path | success | errors |
|---|---|---|
| `POST /jobs` | `202` job created | `400` path missing or outside `MEDIA_ROOT`, or unknown model; `422` malformed body |
| `GET /jobs/{id}` | `200` status object | `404` unknown id |
| `GET /jobs/{id}/result` | `200` whisperX JSON | `404` unknown id; `409` job not `succeeded` |
| `DELETE /jobs/{id}` | `204` | `404` unknown id |
| `GET /info` | `200` version, diarization, model names and the default | — |
| `GET /health` | `200` `{"status": "ok", "version": ...}` | — |

```json
// POST /jobs
{"path": "user_files/abc/interview.mp4", "model": "large-v3", "language": "de",
 "diarize": false}
// 202
{"id": "j_8f3ab2c1", "status": "queued"}

// GET /jobs/j_8f3ab2c1
{"id": "j_8f3ab2c1", "status": "running", "progress": 0.65,
 "created_at": "2026-07-08T14:02:11+00:00",
 "started_at": "2026-07-08T14:05:03+00:00", "finished_at": null,
 "language": "de", "model": "large-v3", "error": null}

// GET /info
{"version": "0.5.0", "diarization": true, "default_model": "large-v3",
 "models": [{"name": "large-v3", "description": "Whisper large-v3"}]}
```

`status` is one of `queued | running | failed | succeeded`; `progress` is a
monotonically increasing fraction in `[0, 1]`. `DELETE` cancels a queued job
and removes a finished one; on a running job it marks the job for cleanup
once it finishes. Unknown ids are `404`, also after data loss — callers treat
that as "gone, resubmit".

`model` names an entry of the model registry (see below); `null` or a
missing `model` selects the default. The resolved name is stored with the job,
reported in its status and written into the result as `model`. A job created
before models could be selected reports `"model": null` and runs with the
default.

Diarization (`diarize: true`) attaches a speaker to every word, using the
gated pyannote models. It needs `HF_TOKEN`; without it the job fails before any
transcription work runs.

`GET /health` answers as soon as the process serves requests and is what
the container health check calls. It reports the version from the `VERSION`
file and says nothing about the worker, the spool or the model cache: a
healthy response does not mean a job can run.

## Queue

The queue is a spool directory, one subdirectory per job — no Redis, no
database:

```
spool/
  j_8f3ab2c1/
    job.json      # the single source of truth for the job
    result.json   # whisperX output (present iff succeeded)
```

Order is derived by scanning, never stored. One worker thread picks the
oldest queued job. Because the spool lives on a volume, a container restart
loses no jobs: jobs found `running` at startup were interrupted and are reset
to `queued`.

## Configuration

| var | default | notes |
|---|---|---|
| `MEDIA_ROOT` | — | mount point of the shared media storage (read-only) |
| `SPOOL_DIR` | `./spool` | volume in production |
| `RETENTION_DAYS` | `7` | finished jobs are swept after this |
| `MODELS_FILE` | `/etc/mmt-asr/models.toml` | the model registry, see below |
| `WHISPERX_DEVICE` | `cuda` | applies to every model |
| `HF_HOME` | `/model_cache` | model cache; a volume in production |
| `HF_TOKEN` | — | gated diarization models only |
| `ALIGN_LANGUAGES` | `de en` | read by `prefetch.py` only, not by the service |

## Models

The models a job can run with are configured in a TOML registry file, which is
read once at startup. A change to the file takes effect after a restart. An
invalid file stops the service from starting, with an error that names the
offending key or model.

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

| key | default | notes |
|---|---|---|
| `default` | — | required; the name of an entry of `models` |
| `models.<name>` | — | at least one; the name matches `^[a-z0-9][a-z0-9._-]*$` |
| `source` | — | required; a Hugging Face model name, or an absolute path to a local model |
| `compute_type` | `float16` | `int8_float16` if VRAM is tight |
| `batch_size` | `16` | lower to fit VRAM |
| `description` | `""` | returned by `GET /info` |

A `source` that starts with `/` is a local model and must be an existing
directory in the CTranslate2 format that faster-whisper loads, for example the
output of `ct2-transformers-converter`. A fine-tuned Hugging Face checkpoint
has to be converted before it can be used.

The service keeps one whisper model loaded. A job that needs a different model
releases the loaded one and loads its own, so GPU memory use stays that of
the largest configured model.

The image ships `models.toml` at `/etc/mmt-asr/models.toml`, with `large-v3`
as the only model. In production two read-only mounts replace and extend it,
and `MODELS_FILE` is not set:

* the host's registry file over `/etc/mmt-asr/models.toml`
  (`models_file` in `deploy/create-mmt-asr`),
* the host directory with the local model directories at `/models`
  (`models_dir`). A local `source` names the path inside the
  container, for example `/models/large-v3-verbatim-v1`.

## Development

The tests fake whisperx as a module, so they need neither a GPU nor the torch
wheels:

```
uv sync --group dev
uv run pytest
```

Running the service for real additionally needs whisperx, `ffmpeg`, and a
CUDA GPU. `/etc/mmt-asr` exists only in the container, so a local run points
`MODELS_FILE` at `models.dev.toml`, which offers the `small` model:

```
uv sync --extra whisperx
MEDIA_ROOT=/path/to/media MODELS_FILE=models.dev.toml uv run uvicorn api:app --reload
```

Once the server is running, open http://localhost:8000/docs in your browser
to access the interactive API documentation.

## Model weights

The image contains no model weights. `HF_HOME` points at `/model_cache`,
which is a volume in production, and a model is downloaded the first time a
job needs it. Two reasons: the diarization models are gated on Hugging Face
and must not be redistributed in a public image, and weights built into the
image would only be used when they match a model of the mounted registry.

`prefetch.py` moves that download out of the first job by populating the
volume in advance. It reads the same registry as the service and downloads
every model whose `source` is a Hugging Face name; local models are skipped.
The registry checks that each local `source` exists, so the model directory is
mounted as well:

```
podman run --rm \
       --volume mmt-asr-models:/model_cache \
       --volume /path/to/models.toml:/etc/mmt-asr/models.toml:ro \
       --volume /path/to/models:/models:ro \
       --env ALIGN_LANGUAGES="de en" \
       --env HF_TOKEN=... \
       ghcr.io/asr4memory/mmt-asr:TAG python prefetch.py
```

It loads every model on the CPU, so it needs no GPU device, and it downloads
the diarization pipeline only when `HF_TOKEN` is set. Files already in the
volume are not downloaded again.
