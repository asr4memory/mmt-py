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
| `POST /jobs` | `202` job created | `400` path missing or outside `MEDIA_ROOT`; `422` malformed body |
| `GET /jobs/{id}` | `200` status object | `404` unknown id |
| `GET /jobs/{id}/result` | `200` whisperX JSON | `404` unknown id; `409` job not `succeeded` |
| `DELETE /jobs/{id}` | `204` | `404` unknown id |

```json
// POST /jobs
{"path": "user_files/abc/interview.mp4", "language": "de", "diarize": false}
// 202
{"id": "j_8f3ab2c1", "status": "queued"}

// GET /jobs/j_8f3ab2c1
{"id": "j_8f3ab2c1", "status": "running", "progress": 0.65,
 "created_at": "2026-07-08T14:02:11+00:00",
 "started_at": "2026-07-08T14:05:03+00:00", "finished_at": null,
 "language": "de", "error": null}
```

`status` is one of `queued | running | failed | succeeded`; `progress` is a
monotonically increasing fraction in `[0, 1]`. `DELETE` cancels a queued job
and removes a finished one; on a running job it marks the job for cleanup
once it finishes. Unknown ids are `404`, also after data loss — callers treat
that as "gone, resubmit".

Diarization (`diarize: true`) is not implemented yet; such jobs fail.

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
| `WHISPERX_MODEL` | `large-v3` | |
| `WHISPERX_DEVICE` | `cuda` | |
| `WHISPERX_COMPUTE_TYPE` | `float16` | `int8_float16` if VRAM is tight |
| `WHISPERX_BATCH_SIZE` | `16` | lower to fit VRAM |
| `HF_HOME` | `/model_cache` | model cache; a volume in production |
| `HF_TOKEN` | — | gated diarization models only |
| `ALIGN_LANGUAGES` | `de en` | read by `prefetch.py` only, not by the service |

## Development

The tests fake whisperx as a module, so they need neither a GPU nor the torch
wheels:

```
uv sync --group dev
uv run pytest
```

Running the service for real additionally needs whisperx, `ffmpeg`, and a
CUDA GPU:

```
uv sync --extra whisperx
MEDIA_ROOT=/path/to/media WHISPERX_MODEL=small uv run uvicorn api:app --reload
```

Once the server is running, open http://localhost:8000/docs in your browser
to access the interactive API documentation.

## Model weights

The image contains no model weights. `HF_HOME` points at `/model_cache`,
which is a volume in production, and a model is downloaded the first time a
job needs it. Two reasons: the diarization models are gated on Hugging Face
and must not be redistributed in a public image, and weights built into the
image would only be used when they match the runtime `WHISPERX_MODEL`.

`prefetch.py` moves that download out of the first job by populating the
volume in advance:

```
podman run --rm \
       --volume mmt-asr-models:/model_cache \
       --env WHISPERX_MODEL=large-v3 \
       --env ALIGN_LANGUAGES="de en" \
       --env HF_TOKEN=... \
       ghcr.io/asr4memory/mmt-asr:TAG python prefetch.py
```

It loads every model on the CPU, so it needs no GPU device, and it downloads
the diarization pipeline only when `HF_TOKEN` is set. Files already in the
volume are not downloaded again.
