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

`TAG` is the image tag to pull from `ghcr.io/asr4memory/mmt-app`. Three kinds
of tag exist, for that image and for the other three as well: a version such as
`2026.9.18`, which is published once and from then on always refers to the same
image; a commit hash, which is published for every build and is likewise fixed;
and `latest`, which follows the newest build of master and therefore moves.
Production uses a version.

The version tag of `mmt-app` is built from the git tag that `release.sh`
creates, so it holds exactly the released code. The ASR, NER and nginx images
have no release tag in git; their version tag is published by the first build
that carries a new version in `asr/VERSION`, `ner/pyproject.toml` or
`nginx/VERSION`, and later builds of the same version leave it as it is.

| Script | Container | Notes |
| --- | --- | --- |
| `create-mmt-app-web` | `mmt-app-web` | Django web app under gunicorn with 4 processes and 8 threads each. Capped at 1.5 GB RAM, published on the host port given by `$MMT_WEB_PORT`. |
| `create-mmt-app-celery` | `mmt-app-celery` | Celery worker with embedded beat (`--beat`) for the default queue. `--concurrency=2`, CPU weight 512, capped at 768 MB RAM + 512 MB swap. |
| `create-mmt-app-media` | `mmt-app-media` | Celery worker for the `media` queue: the web video and the waveform, which run ffmpeg over a whole file. `--concurrency=1`, so one of these tasks runs at a time. CPU weight 256, capped at 1 GB RAM + 512 MB swap. |
| `create-mmt-ner` | `mmt-ner` | NER service as a Celery worker that takes jobs from the `ner` queue one at a time. CPU weight 256, capped at 3 GB RAM. Publishes no port. |
| `create-mmt-asr` | `mmt-asr` | FastAPI ASR (whisperX) service. Needs the GPU (CDI), a `mmt-asr-spool` volume for its job queue, a `mmt-asr-models` volume for the model cache and the media storage mounted read-only. Published on `$MMT_ASR_PORT`. |
| `create-mmt-nginx` | `mmt-nginx` | Reverse proxy in front of the web app. Terminates TLS, serves the media files (see below) and has a maintenance mode. The image is `ghcr.io/asr4memory/mmt-nginx`, its tag is the version in `nginx/VERSION`. Published on `$MMT_HTTPS_PORT`, and on `$MMT_HTTP_PORT`, where it only redirects to HTTPS. |

The directory `podman/` holds Quadlet units for the same containers, plus the
database and Redis, as an alternative to the scripts (see "Quadlet units"
below).

No container has a CPU limit. The containers have CPU weights instead: a
container uses CPUs that are idle, and when containers compete for CPU, each
receives CPU time in proportion to its weight. The web app and nginx keep the
default weight of 1024, the default Celery worker has 512, and the media worker
and the NER service have 256 each.

The web app handles at most 32 requests at once, one per gunicorn thread.
Without the nginx container, every media transfer, download and upload chunk
holds one of the 32 threads while it is in progress.

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
| `MMT_DATA_DIR` | `create-mmt-app-web`, `create-mmt-app-celery`, `create-mmt-app-media`, `create-mmt-nginx` | Host directory bind-mounted as the app's user files. |
| `MMT_WEB_PORT` | `create-mmt-app-web` | Host port the web app is published on. |
| `MMT_HTTP_PORT` | `create-mmt-nginx` | Host port for plain HTTP, which the proxy redirects to HTTPS on port 443. |
| `MMT_HTTPS_PORT` | `create-mmt-nginx` | Host port for HTTPS. |
| `MMT_TLS_DIR` | `create-mmt-nginx` | Host directory that holds the certificate chain as `fullchain.pem` and the private key as `privkey.pem`. |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | `create-mmt-ner` | The Redis URLs from the app's `env.list`, as seen from inside the NER container. |
| `MMT_ASR_PORT` | `create-mmt-asr` | Host port the ASR service is published on. |
| `MMT_MEDIA_ROOT` | `create-mmt-asr` | Host directory holding the media files, mounted read-only as the ASR service's `MEDIA_ROOT`. |
| `WHISPERX_MODEL`, `WHISPERX_DEVICE`, `WHISPERX_COMPUTE_TYPE`, `WHISPERX_BATCH_SIZE`, `HF_TOKEN` | `create-mmt-asr` | Optional. Forwarded into the container where set; the service's own defaults apply otherwise. |

## Periodic tasks

`CELERY_BEAT_SCHEDULE` in `app/mmt/settings/base.py` holds the periodic tasks, at
present the sweep that polls running transcription jobs every 60 seconds. Beat
runs embedded in the worker (`celery worker --beat`) rather than as a separate
process. Only `mmt-app-celery` is started with `--beat`, so there is exactly one
beat regardless of `--concurrency`, which adds pool processes only. The media
worker runs without `--beat`. The Celery manual does not recommend `--beat` for
production; the tradeoff is accepted while one worker node runs beat. A second
worker node started with `--beat` would start a second beat, and every periodic
task would then be sent twice.

## Media queue

`CELERY_TASK_ROUTES` in `app/mmt/settings/base.py` sends the web video and the
waveform tasks to the `media` queue, which only `mmt-app-media` consumes. The
other tasks, among them the duration, which reads only the file header, stay in
the default queue of `mmt-app-celery`. Start `mmt-app-media` before deploying
an app version with these routes; until it runs, the media tasks wait in the
queue.

The app reaches the ASR service at `ASR_API_URL` (see `env.list`). It reaches
the NER service through Redis: it sends the task `ner.extract` to the `ner`
queue, and the NER worker sends the result back to the app's worker as the task
`store_entities`. `CELERY_RESULT_BACKEND` holds the states of the NER tasks;
the app reads it for the exception of a failed task.
`ASR_API_URL` also switches the
transcription feature on: a deployment that runs no ASR service leaves the
variable unset, and the app then shows no transcription section on a file's page
and refuses a transcription request.

## ASR model cache

The ASR image contains no model weights (the diarization models are gated on
Hugging Face and must not be redistributed). Weights live in the
`mmt-asr-models` volume and are downloaded on first use. To download them
before the first job, run the prefetch command documented in
[`asr/README.md`](../asr/README.md) against the same volume.

## Media files

`mmt-nginx` sits in front of the web app and serves the media files from disk
instead of letting them pass through Django. The view still runs the same
permission check and then answers with an empty body and an `X-Accel-Redirect`
header naming a location that is `internal`, which nginx cannot be asked for
from outside. nginx serves the file, handling `Range` requests itself.

This is switched on by `X_ACCEL_LOCATION=/internal-media/` in `env.list`.
Without the variable the app serves the files itself, which is what
development and the test suite do.

Set the variable only once nginx is actually in front of the web app,
otherwise clients receive an empty `200` and no media. The order is:

1. Run `create-mmt-nginx TAG` and direct the HTTPS traffic to
   `$MMT_HTTPS_PORT` instead of `$MMT_WEB_PORT`.
2. Add `X_ACCEL_LOCATION=/internal-media/` to `env.list` and recreate the web
   container so it reads the variable.

The proxy configuration is `nginx/default.conf` in this repository.
It is copied into the `mmt-nginx` image; a change to the configuration is a new
image version. The user files directory is mounted read-only at
`/srv/user_files`, so it must be the same
host directory that `$MMT_DATA_DIR` names.

The nginx worker processes in the image run as uid 999, the uid of the app
user in the app image. The user files are readable by their owner and group
only (the production storage is a CIFS mount with `file_mode=0640` and
`dir_mode=0750`), and the official nginx image runs its workers as uid 101,
which cannot open them. Under rootless podman, both containers translate uid
999 to the same host uid, so the proxy reads the files as their owner.

## TLS

`mmt-nginx` terminates TLS and forwards the requests to the web app over
plain HTTP, with the header `X-Forwarded-Proto: https`, from which Django
recognises the request as secure. Plain HTTP requests are answered with a
redirect to `https://` on port 443, so the proxy has to be reachable from
outside on the standard ports 80 and 443.

The certificate and the key are read from `$MMT_TLS_DIR`, mounted read-only at
`/etc/nginx/tls`. The nginx master process reads them as root inside the
container, which under rootless podman is the host user that runs podman, so
the files must be readable by that user. nginx reads the files only at startup
and on a reload; after a renewal of the certificate, reload it with:

```
podman exec mmt-nginx nginx -s reload
```

## Maintenance mode

While maintenance mode is on, the proxy answers every request with status
`503` and the maintenance page (`nginx/maintenance.html`), and forwards no
request to the web app. The web app and the workers keep running.

```
./mmt-maintenance on
./mmt-maintenance off
```

The script creates or removes the flag file `/srv/maintenance/enabled` in the
`mmt-nginx` container. nginx checks for the file on every request, so no reload
is needed. The file survives a restart of the container, but not its removal:
a recreated proxy container starts with maintenance mode off.

## Network

`mmt-nginx` and `mmt-app-web` are connected to the podman network `mmt`, and
the proxy reaches the web app as `mmt-app-web:8000`. The network has to exist
before either script runs; it is created once with `podman network create mmt`,
or by the Quadlet unit `podman/mmt.network`.

## Quadlet units

The files in `podman/` are [Quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
units. At `systemctl --user daemon-reload`, podman generates a systemd service
from each of them, so systemd starts, restarts and orders the containers.
podman 5.0 or later is required.

| Unit | Container | Notes |
| --- | --- | --- |
| `mmt.network` | | The network `mmt`, on which all containers reach each other by container name. |
| `mmt-mariadb.container`, `mmt-mariadb.volume` | `mmt-mariadb` | MariaDB 11 with its data in the volume `mmt-mariadb`. |
| `mmt-redis.container`, `mmt-redis.volume` | `mmt-redis` | Redis 8 with its data in the volume `mmt-redis`. |
| `mmt-app-web.container` | `mmt-app-web` | As `create-mmt-app-web`, but publishes no port. |
| `mmt-app-celery.container` | `mmt-app-celery` | As `create-mmt-app-celery`. |
| `mmt-app-media.container` | `mmt-app-media` | As `create-mmt-app-media`. |
| `mmt-ner.container` | `mmt-ner` | As `create-mmt-ner`. |
| `mmt-nginx.container` | `mmt-nginx` | As `create-mmt-nginx`. |

The ASR service runs on another host and has no unit.

A unit that references the network or a volume starts after it. The app units
start after the database and Redis, which report themselves as started only
once their health check passes (`Notify=healthy`), and the proxy starts after
the web app.

Quadlet does not read environment variables, so the host-specific values are
written into the units: the image tags, the host ports of the proxy, the user
files directory `/srv/mmt/user_files` and the TLS directory `/srv/mmt/tls`.
Adjust them on the host. The Celery workers have fixed host names, because
systemd would replace the `%h` in their worker names with the home directory.

Installation, as the user that runs the containers:

1. Create `~/mmt/app.env` with the content of `env.list` (see "Secrets") and
   `DATABASE_HOST=mmt-mariadb`, `DATABASE_USER=mmt`, and `redis://mmt-redis`
   as `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`.
2. Create `~/mmt/mariadb.env` with `MARIADB_ROOT_PASSWORD` and
   `MARIADB_PASSWORD`; the latter is the same as `DATABASE_PASSWORD` in
   `app.env`. MariaDB reads both only when it initialises an empty volume.
3. Copy the files in `podman/` to `~/.config/containers/systemd/` and run
   `systemctl --user daemon-reload`.
4. Run `loginctl enable-linger` once, so that the services start at boot
   without a login session.
5. Allow rootless containers to publish the ports 80 and 443 by setting the
   sysctl `net.ipv4.ip_unprivileged_port_start` to 80 or lower.
6. Start the containers with
   `systemctl --user start mmt-nginx mmt-app-celery mmt-app-media mmt-ner`;
   the units they depend on start first.

To deploy a new image version, change the tag in the unit, run
`systemctl --user daemon-reload` and restart the service.

## Secrets

The scripts expect an `env.list` file in the working directory on the server
(passed via `--env-file`). It holds secrets and is **not** committed.
