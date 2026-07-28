# Deployment scripts

Production runs the application as individual [podman](https://podman.io/)
containers, each created by a script in this directory. This is the current
production deployment method.

`docker/docker-compose.yml` is **dev only** — for spinning up the stack
locally to test the container images. Keep resource settings there in sync
with the production scripts so dev mirrors prod.

## Scripts

Each `create-*` script runs one container. Usage:

```
./create-mmt-app-celery TAG    # e.g. ./create-mmt-app-celery 1.4.2
```

`TAG` is the image tag to pull from `ghcr.io/asr4memory/mmt-app`.

| Script | Container | Notes |
| --- | --- | --- |
| `create-mmt-app-web` | `mmt-app-web` | Django web app. Capped at 1.5 GB RAM, published on the host port given by `$MMT_WEB_PORT`. |
| `create-mmt-app-celery` | `mmt-app-celery` | Celery worker with embedded beat (`-B`). `--concurrency=4` (4-core host), capped at 1 GB RAM + 512 MB swap. |
| `create-mmt-ner` | `mmt-ner` | FastAPI NER service. Capped at 3 GB RAM, published on the host port given by `$MMT_NER_PORT`. |
| `create-mmt-asr` | `mmt-asr` | FastAPI ASR (whisperX) service. Needs the GPU (CDI), a `mmt-asr-spool` volume for its job queue, a `mmt-asr-models` volume for the model cache and the media storage mounted read-only. Published on `$MMT_ASR_PORT`. |

To change an already-running container, stop and remove it, then re-run its
script:

```
podman stop mmt-app-celery && podman rm mmt-app-celery
./create-mmt-app-celery TAG
```

## Environment

Host-specific values are passed as environment variables so they stay out of
version control. Set them in the shell on the server before running a script
(the script aborts if a required variable is unset):

| Variable | Used by | Meaning |
| --- | --- | --- |
| `MMT_DATA_DIR` | `create-mmt-app-web`, `create-mmt-app-celery` | Host directory bind-mounted as the app's user files. |
| `MMT_WEB_PORT` | `create-mmt-app-web` | Host port the web app is published on. |
| `MMT_NER_PORT` | `create-mmt-ner` | Host port the NER service is published on. |
| `MMT_ASR_PORT` | `create-mmt-asr` | Host port the ASR service is published on. |
| `MMT_MEDIA_ROOT` | `create-mmt-asr` | Host directory holding the media files, mounted read-only as the ASR service's `MEDIA_ROOT`. |
| `WHISPERX_MODEL`, `WHISPERX_DEVICE`, `WHISPERX_COMPUTE_TYPE`, `WHISPERX_BATCH_SIZE`, `HF_TOKEN` | `create-mmt-asr` | Optional. Forwarded into the container where set; the service's own defaults apply otherwise. |

## Periodic tasks

`CELERY_BEAT_SCHEDULE` in `app/mmt/settings.py` holds the periodic tasks, at
present the sweep that polls running transcription jobs every 60 seconds. Beat
runs embedded in the worker (`celery worker -B`) rather than as a separate
process. The container runs a single worker node, so `-B` starts exactly one
beat regardless of `--concurrency`, which adds pool processes only. The Celery
manual does not recommend `-B` for production; the tradeoff is accepted while
there is one worker node. Starting a second worker node, for example a second
container, would start a second beat, so beat has to move into its own process
as part of any such change.

The app reaches the ASR service at `ASR_API_URL` (see `env.list`), the same way
it reaches the NER service at `NER_API_URL`. `ASR_API_URL` also switches the
transcription feature on: a deployment that runs no ASR service leaves the
variable unset, and the app then shows no transcription section on a file's page
and refuses a transcription request.

## ASR model cache

The ASR image contains no model weights (the diarization models are gated on
Hugging Face and must not be redistributed). Weights live in the
`mmt-asr-models` volume and are downloaded on first use. To download them
before the first job, run the prefetch command documented in
[`asr/README.md`](../asr/README.md) against the same volume.

## Secrets

The scripts expect an `env.list` file in the working directory on the server
(passed via `--env-file`). It holds secrets and is **not** committed.

## TODO

Bring any remaining production setup under version control here
(e.g. db/redis/proxy).
