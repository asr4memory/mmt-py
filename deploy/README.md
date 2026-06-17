# Deployment scripts

Production runs the application as individual [podman](https://podman.io/)
containers, each created by a script in this directory. This is the current
production deployment method.

- `docker/docker-compose.yml` is **dev only** — for spinning up the stack
  locally to test the container images. Keep resource settings here in sync
  with the production scripts so dev mirrors prod.
- The `ansible/` directory is **legacy** and no longer used to deploy.

## Scripts

Each `create-*` script runs one container. Usage:

```
./create-mmt-app-celery TAG    # e.g. ./create-mmt-app-celery 1.4.2
```

`TAG` is the image tag to pull from `ghcr.io/asr4memory/mmt-app`.

| Script | Container | Notes |
| --- | --- | --- |
| `create-mmt-app-web` | `mmt-app-web` | Django web app. Capped at 1.5 GB RAM, published on the host port given by `$MMT_WEB_PORT`. |
| `create-mmt-app-celery` | `mmt-app-celery` | Celery worker. `--concurrency=4` (4-core host), capped at 1 GB RAM + 512 MB swap. |
| `create-mmt-ner` | `mmt-ner` | FastAPI NER service. Capped at 3 GB RAM, published on the host port given by `$MMT_NER_PORT`. |

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

## Secrets

The scripts expect an `env.list` file in the working directory on the server
(passed via `--env-file`). It holds secrets and is **not** committed.

## TODO

Bring any remaining production setup under version control here
(e.g. db/redis/proxy).
