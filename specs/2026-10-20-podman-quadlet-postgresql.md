# Production on Quadlet and PostgreSQL

This is an executable spec. It is the authoritative record of the decisions for
moving the production VM to containers managed by Quadlet and from MariaDB to
PostgreSQL. An implementing session works from this document and resolves
ambiguity by reading it.

## Motivation

On the production VM, the application containers are started by the
`deploy/create-*` scripts with `podman run --restart always`. MariaDB, Redis
and the nginx that terminates TLS run as host services outside of containers
and outside of version control. The containers reach each other and the host
services through published host ports and `host.containers.internal`.

After this change, every service on the VM runs in a podman container, every
container is described by a Quadlet unit file in this repository, and the
database is PostgreSQL. systemd starts the containers at boot in dependency
order, restarts them when they exit and collects their logs in journald. The
containers reach each other by name on one podman network, as they do in
`docker/docker-compose.yml`.

## Non-goals

- **No pods.** All containers in a pod share one network namespace, so two
  services that listen on the same port cannot run in one pod. The containers
  are joined by a podman network instead.
- **No `podman kube play` and no compose in production.**
- **No change to the ASR deployment.** The ASR service runs on a separate host.
  `deploy/create-mmt-asr` stays as it is, and the app reaches the service at
  `ASR_API_URL` as before.
- **No automatic image updates** (`AutoUpdate=`). An image changes only through
  `deploy/set-version`.
- **No replication, point-in-time recovery or connection pooling** for
  PostgreSQL. The only backup is the daily dump.
- **No resource caps for PostgreSQL and Redis.** They keep the default CPU
  weight and have no memory limit.
- **No change to the `migrate` in `app/entrypoint.sh`.** Each app container
  still runs `migrate` at startup, so the three app containers can run it at
  the same time. Fixing this is a separate change.
- **No change to the user files storage.** It stays on the CIFS mount.

## Feature reference

### Account and directories

All containers run rootless as the service account `mmt`. All files live in
the home directory of `mmt`, so a deploy does not need root.

| Path | Content |
| --- | --- |
| `~mmt/.config/containers/systemd/` | The installed Quadlet units and their image drop-ins. |
| `~mmt/.config/systemd/user/` | The installed backup service and timer. |
| `~mmt/env.list` | The app environment, as today. Not in version control. |
| `~mmt/ner.env` | `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` for the NER container. Not in version control. |
| `~mmt/user_files` | A symlink to the user files directory on the CIFS mount. The units mount this path, so the host-specific location appears in one place only. |
| `~mmt/backups/postgres/` | The daily database dumps. |
| `~mmt/migration/` | The data dump of slice 4. Deleted in slice 6. |

The deploy scripts run as `mmt` from a checkout of this repository on the VM.
A shell for `mmt` with a working `systemctl --user` is opened with
`sudo machinectl shell mmt@`.

Root sets the following once:

- `loginctl enable-linger mmt`, so the user units of `mmt` start at boot
  without a login.
- In slice 5 only, `net.ipv4.ip_unprivileged_port_start=80` in
  `/etc/sysctl.d/`, so the rootless nginx container can publish ports 80 and 443.

### Units

The units live in `deploy/quadlet/`. A `.container` file named `X.container`
becomes the systemd service `X.service`.

| Unit | Container name | Image | Notes |
| --- | --- | --- | --- |
| `mmt.network` | – | – | `NetworkName=mmt`. |
| `mmt-app-web.container` | `mmt-app-web` | `ghcr.io/asr4memory/mmt-app` | Publishes no port. |
| `mmt-app-celery.container` | `mmt-app-celery` | `ghcr.io/asr4memory/mmt-app` | Default queue with `--beat`. |
| `mmt-app-media.container` | `mmt-app-media` | `ghcr.io/asr4memory/mmt-app` | `media` queue. |
| `mmt-ner.container` | `mmt-ner` | `ghcr.io/asr4memory/mmt-ner` | `EnvironmentFile=%h/ner.env`. |
| `mmt-nginx.container` | `mmt-nginx` | `ghcr.io/asr4memory/mmt-nginx` | The only container that publishes a port. |
| `mmt-redis.container` | `mmt-redis` | `docker.io/library/redis:7` | Slice 3. |
| `mmt-redis.volume` | – | – | `VolumeName=mmt-redis`, mounted at `/data`. |
| `mmt-postgres.container` | `mmt-postgres` | `docker.io/library/postgres:18` | Slice 4. |
| `mmt-postgres.volume` | – | – | `VolumeName=mmt-postgres`, mounted at `/var/lib/postgresql`. |

Every `.container` unit has `Network=mmt.network`, `ContainerName=` as in the
table, `[Service] Restart=always` and `[Install] WantedBy=default.target`. The
other containers reach a container by its container name.

The units carry over the settings of the `create-*` scripts:

- `RunInit=true` wherever the script passes `--init`.
- `HealthCmd=` and the other health settings as in the script.
- `--memory`, `--memory-swap` and `--cpu-shares` in `PodmanArgs=`.
- `EnvironmentFile=%h/env.list` for the three app units.
- `Volume=%h/user_files:/app/django-app/user_files` for the three app units,
  and `Volume=%h/user_files:/srv/user_files:ro` for nginx.

The Celery units set a fixed `HostName=` equal to the container name and name
the Celery node after it, for example
`Exec=celery --app=mmt worker --hostname=celery@mmt-app-celery ...` and
`HealthCmd=celery --app=mmt inspect ping --destination=celery@mmt-app-celery`.
This is required because systemd expands `%h` in a unit file to the home
directory, and `$(hostname)` in a health command would need a shell. The NER
unit does the same with `ner@mmt-ner`.

From slice 3 on, the app units and `mmt-ner` have
`Requires=mmt-redis.service` and `After=mmt-redis.service`. From slice 4 on,
the app units also have `Requires=mmt-postgres.service` and
`After=mmt-postgres.service`. `mmt-nginx` has `After=mmt-app-web.service` and no
`Requires=`, so nginx keeps running while the web container restarts.

`mmt-nginx` sets `MMT_WEB_UPSTREAM=mmt-app-web:8000` and
`NGINX_ENVSUBST_FILTER=^MMT_`. Until slice 5 it publishes
`127.0.0.1:8080:8080`, and the host nginx forwards to `127.0.0.1:8080`.

`mmt-postgres` sets `POSTGRES_USER=mmt` and `POSTGRES_DB=mmt`, takes
`POSTGRES_PASSWORD` from the podman secret `mmt-postgres-password`
(`Secret=mmt-postgres-password,type=env,target=POSTGRES_PASSWORD`), and has
`HealthCmd=pg_isready --username=mmt --dbname=mmt`. It publishes no port. The
database keeps the image's default locale.

### Image versions

A unit file in the repository has no `Image=` line. The image and its tag are
set in the drop-in `~/.config/containers/systemd/<unit>.container.d/10-image.conf`,
which `deploy/set-version` writes. PostgreSQL and Redis have their image in the
unit file, because their version changes with the repository and not with a
deploy.

```
deploy/install-units
```

Copies `deploy/quadlet/*` to `~/.config/containers/systemd/` and
`deploy/systemd/*` to `~/.config/systemd/user/`, then runs
`systemctl --user daemon-reload`. It does not touch the drop-ins and does not
start or restart a unit.

```
deploy/set-version COMPONENT TAG
```

`COMPONENT` is `app`, `ner` or `nginx`. The script pulls the image, writes the
drop-in of every unit of the component, runs `systemctl --user daemon-reload`
and restarts those units. `app` covers `mmt-app-web`, `mmt-app-celery` and
`mmt-app-media`, which therefore always run the same version. An unknown
component or a missing argument prints the usage and exits with status 1.

### Environment

The database password is the podman secret `mmt-postgres-password`, created
once with `podman secret create mmt-postgres-password -` from standard input.
The app units read it with
`Secret=mmt-postgres-password,type=env,target=DATABASE_PASSWORD`, and
`env.list` no longer contains `DATABASE_PASSWORD`, so the value exists in one
place only.

After slice 4, `env.list` contains:

```
DATABASE_ENGINE=postgresql
DATABASE_HOST=mmt-postgres
DATABASE_PORT=5432
DATABASE_NAME=mmt
DATABASE_USER=mmt
CELERY_BROKER_URL=redis://mmt-redis
CELERY_RESULT_BACKEND=redis://mmt-redis
```

`ner.env` contains the same two Celery lines.

### PostgreSQL compatibility in the code

- `segment_count` in `TranscriptQuerySet.with_statistics` uses `JSON_LENGTH`,
  which PostgreSQL does not have. It becomes a `Func` subclass
  `JSONArrayLength` in `transcripts/models.py` with an `as_mysql` that renders
  `JSON_LENGTH(content, '$.segments')` and an `as_postgresql` that renders
  `CASE WHEN jsonb_typeof(content -> 'segments') = 'array' THEN
  jsonb_array_length(content -> 'segments') END`. Both return NULL when
  `segments` is missing, which matches the `None` of `derive_statistics`. The
  `CASE` is needed because `jsonb_array_length` raises an error for a value
  that is not an array.
- MariaDB compares strings case-insensitively, and PostgreSQL compares them
  case-sensitively. Case-insensitive uniqueness is kept where it matters:
  - The constraint `unique_filename` on `UploadedFile` becomes a unique
    constraint on `Lower('filename')` and `project`. The existence check in
    `projects/views.py` uses `filename__iexact`. Without this, a project could
    hold `A.mp4` and `a.mp4`, and on a case-insensitive file system the second
    upload would overwrite the first.
  - `Tag.name` gets a unique constraint on `Lower('name')` in place of
    `unique=True`.
  - Usernames are lowercase through their validator, allauth normalizes email
    addresses itself, and group and feature flag names are defined in code.
    These stay as they are.

  MariaDB does not support expression indexes. Django skips the two
  constraints there and emits a system check warning until slice 6. The view
  check applies on both databases.

### Data migration

The data is copied with Django's `dumpdata` and `loaddata`, which convert the
types through the ORM. Django creates the schema in PostgreSQL with `migrate`.
The dump excludes `contenttypes`, `auth.permission`, `sessions` and `silk`, and
uses `--natural-foreign --natural-primary`, so that content types and
permissions are matched by name instead of by ID. All users have to log in
again. `loaddata` resets the PostgreSQL sequences itself.

A one-off management command `count_rows` in `mmt/core` prints one line
`app_label.ModelName count` per model, sorted, and leaves out the excluded
models. Its output before and after the copy must be identical. The command is
removed in slice 6.

### Backup

`deploy/systemd/mmt-postgres-backup.service` runs
`podman exec mmt-postgres pg_dump --format=custom --username=mmt mmt` into
`~mmt/backups/postgres/mmt-YYYY-MM-DD.dump` and deletes dumps older than 14
days. `mmt-postgres-backup.timer` runs it daily at 03:00 with
`Persistent=true`.

## Open decisions

- **TLS certificates (slice 5).** It is not yet decided how the certificates
  are obtained (ACME in a container or files provided by the university), nor
  how the TLS configuration enters the `mmt-nginx` image without breaking the
  plain-HTTP setup of the dev compose file. Both are written into this spec
  before slice 5 starts.

## File layout

```
app/mmt/transcripts/models.py          JSONArrayLength(Func)
app/mmt/uploaded_files/models.py       unique constraint on Lower('filename'), project
app/mmt/my_account/models.py           unique constraint on Lower('name')
app/mmt/projects/views.py              filename__iexact existence check
app/mmt/core/management/commands/count_rows.py   one-off, slices 4–6
.github/workflows/app-tests.yml        matrix over mysql and postgresql
docker/docker-compose.yml, env.list    db service on postgres:18
deploy/
  README.md                            describes the Quadlet deployment
  install-units
  set-version COMPONENT TAG
  create-mmt-asr                       unchanged, for the ASR host
  quadlet/                             the units listed above
  systemd/
    mmt-postgres-backup.service
    mmt-postgres-backup.timer
```

## Slices

Each slice is deployed on its own.

### Slice 1: PostgreSQL compatibility

Production keeps running on MariaDB.

- [ ] CI runs the backend tests against both MySQL and PostgreSQL (matrix over
  `DATABASE_ENGINE`). The runner's preinstalled PostgreSQL is started the same
  way as MySQL. Done when both matrix jobs run, with the PostgreSQL job failing
  only on the points below.
- [ ] `JSONArrayLength`. Done when the existing `with_statistics` tests pass on
  both databases.
- [ ] Case-insensitive filename uniqueness. Done when a test that uploads
  `a.mp4` into a project holding `A.mp4` is rejected on both databases.
- [ ] Case-insensitive `Tag.name` uniqueness. Done when a test that creates
  `history` next to `History` raises `IntegrityError` on PostgreSQL.
- [ ] The dev compose `db` service runs `postgres:18`, and `docker/env.list`
  matches it. Done when the dev stack starts and migrates.

### Slice 2: Quadlet for the existing containers

The containers still use the host MariaDB and the host Redis; the values in
`env.list` stay as they are.

- [ ] `mmt.network` and the units for web, celery, media, ner and nginx, plus
  `install-units` and `set-version`.
- [ ] `deploy/README.md` describes the Quadlet deployment, the account setup
  and the directories, and no longer describes the `create-*` scripts other than
  `create-mmt-asr`.
- [ ] Switch-over: stop and remove the old containers, run `install-units`,
  run `set-version` for each component, and point the host nginx at
  `127.0.0.1:8080`. Done when `systemctl --user status` shows all five units
  active and healthy, and they are active again after a reboot of the VM.
- [ ] Remove the replaced `create-*` scripts.

Rollback: stop the units and run the `create-*` scripts of the previous
commit.

### Slice 3: Redis in a container

- [ ] `mmt-redis.container`, `mmt-redis.volume` and the `Requires=`/`After=`
  lines on the app and NER units.
- [ ] Switch-over: stop `mmt-app-web`, wait until `LLEN` of `celery`, `media`
  and `ner` in the host Redis is 0 and the workers are idle, stop the workers,
  change the Celery URLs in `env.list` and `ner.env`, start the units, and
  disable the host Redis service. Done when a waveform job and an NER job run
  to completion.

Rollback: restore the old URLs and start the host Redis.

### Slice 4: PostgreSQL in a container

- [ ] `count_rows`. Done when a test shows that it lists a model with its row
  count and leaves out the excluded models.
- [ ] `mmt-postgres.container`, `mmt-postgres.volume`, the `Requires=`/`After=`
  lines and the `Secret=` line on the app units.
- [ ] Backup service and timer. Done when a manual start of the service
  writes a dump that `pg_restore --list` reads.
- [ ] Switch-over, in a maintenance window:
  1. Create the secret, install the units, start `mmt-postgres`.
  2. Stop the app units and `mmt-ner`.
  3. Run `count_rows` and `dumpdata` into `~mmt/migration/` with a one-off
     container of the app image against MariaDB.
  4. Change `env.list` as described under Environment.
  5. Run `loaddata` with a one-off container against PostgreSQL. Its entrypoint
     runs `migrate` first and creates the schema.
  6. Run `count_rows` against PostgreSQL and compare the two outputs.
  7. Start the units. Stop and disable the host MariaDB, but leave its data
     in place.

  Done when the outputs of `count_rows` are identical and the app serves a
  project with its files and transcripts.

Rollback: restore the old `env.list` and start the host MariaDB. Data written
to PostgreSQL after the switch-over is lost.

### Slice 5: TLS in the nginx container

Starts after the open decision on certificates is written into this spec.

- [ ] `mmt-nginx` terminates TLS and publishes ports 80 and 443. The host
  nginx is stopped and disabled.

### Slice 6: Cleanup

- [ ] Remove `mysqlclient`, `libmariadb-dev` in `app/Dockerfile`, the `mysql`
  value of `DATABASE_ENGINE`, the `as_mysql` branch of `JSONArrayLength`, the
  MySQL comments in `transcripts/models.py` and the MySQL job in CI.
- [ ] Remove `count_rows` and `~mmt/migration/`.
- [ ] Remove the host MariaDB, Redis and nginx packages and the MariaDB data.
