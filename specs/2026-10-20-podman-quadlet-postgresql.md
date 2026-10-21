# New server on Quadlet, then PostgreSQL

This is an executable spec. It is the authoritative record of the decisions for
moving production to a new server on which every service runs in a container
managed by Quadlet, and afterwards from MariaDB to PostgreSQL. An implementing
session works from this document and resolves ambiguity by reading it.

## Motivation

On the old server, the application containers are started by the
`deploy/create-*` scripts with `podman run --restart always`. MariaDB, Redis
and the nginx that terminates TLS run as host services outside of containers
and outside of version control. The containers reach each other and the host
services through published host ports and `host.containers.internal`.

Production moves to a new server with 8 CPUs and 24 GB RAM. On the new server,
every service runs in a podman container, every container is described by a
Quadlet unit file in this repository, and the containers reach each other by
name on one podman network, as they do in `docker/docker-compose.yml`. systemd
starts the containers at boot in dependency order, restarts them when they exit
and collects their logs in journald.

The database later changes from MariaDB to PostgreSQL. The server move and the
database change are separate steps: the server move copies the database between
two MariaDB instances, so a problem after either step has one cause, and each
step has its own rollback.

## Non-goals

- **No pods.** All containers in a pod share one network namespace, so two
  services that listen on the same port cannot run in one pod. The containers
  are joined by a podman network instead.
- **No `podman kube play` and no compose in production.**
- **No change to the ASR deployment.** The ASR service runs on a separate host.
  `deploy/create-mmt-asr` stays as it is, and the app reaches the service at
  `ASR_API_URL` as before.
- **No automatic image updates** (`AutoUpdate=`). An app, NER or nginx image
  changes only through `deploy/set-version`.
- **No retuning for the new server.** The units carry over the memory caps,
  CPU weights and concurrency settings of the `create-*` scripts. Using the
  additional CPUs and memory is a separate change.
- **No replication, point-in-time recovery or connection pooling** for the
  database. The only backup is the daily dump.
- **No memory cap for the database containers.**
- **No change to the `migrate` in `app/entrypoint.sh`.** Each app container
  still runs `migrate` at startup, so the three app containers can run it at
  the same time. Fixing this is a separate change.
- **No change to the user files storage.** It stays on the CIFS mount, which
  the new server mounts instead of the old one.

## Feature reference

### Account and directories

All containers run rootless as the service account `mmt`. All files live in
the home directory of `mmt`, so a deploy does not need root.

| Path | Content |
| --- | --- |
| `~mmt/.config/containers/systemd/` | The installed Quadlet units and their image drop-ins. |
| `~mmt/.config/systemd/user/` | The installed backup service and timer. |
| `~mmt/env.list` | The app environment. Not in version control. |
| `~mmt/ner.env` | `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` for the NER container. Not in version control. |
| `~mmt/user_files` | A symlink to the user files directory on the CIFS mount. The units mount this path, so the host-specific location appears in one place only. |
| `~mmt/backups/db/` | The daily database dumps. |
| `~mmt/migration/` | The dumps of the two switch-overs. Deleted in slice 5. |

The deploy scripts run as `mmt` from a checkout of this repository on the
server. A shell for `mmt` with a working `systemctl --user` is opened with
`sudo machinectl shell mmt@`.

Root sets the following once on the new server:

- The package `systemd-container`, which provides `machinectl`.
- `loginctl enable-linger mmt`, so the user units of `mmt` start at boot
  without a login.
- `net.ipv4.ip_unprivileged_port_start=80` in `/etc/sysctl.d/`, so the
  rootless nginx container can publish ports 80 and 443.
- The CIFS mount of the user files, with the same options as on the old
  server.

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
| `mmt-nginx.container` | `mmt-nginx` | `ghcr.io/asr4memory/mmt-nginx` | The only container that publishes ports. |
| `mmt-redis.container` | `mmt-redis` | `docker.io/library/redis:8` | |
| `mmt-redis.volume` | – | – | `VolumeName=mmt-redis`, mounted at `/data`. |
| `mmt-mariadb.container` | `mmt-mariadb` | `docker.io/library/mariadb:11` | Slices 2 to 4. |
| `mmt-mariadb.volume` | – | – | `VolumeName=mmt-mariadb`, mounted at `/var/lib/mysql`. |
| `mmt-postgres.container` | `mmt-postgres` | `docker.io/library/postgres:18` | From slice 4. |
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

The app units and `mmt-ner` have `Requires=mmt-redis.service` and
`After=mmt-redis.service`. The app units also have `Requires=` and `After=` on
the database unit: `mmt-mariadb.service` until slice 4, `mmt-postgres.service`
from slice 4 on. `mmt-nginx` has `After=mmt-app-web.service` and no
`Requires=`, so nginx keeps running while the web container restarts.

`mmt-nginx` sets `MMT_WEB_UPSTREAM=mmt-app-web:8000` and
`NGINX_ENVSUBST_FILTER=^MMT_`, terminates TLS and publishes `80:8080` and
`443:8443`.

`mmt-redis` runs
`Exec=redis-server --maxmemory 200mb --maxmemory-policy noeviction` with
`PodmanArgs=--memory 256m --memory-swap 256m`. With `noeviction`, Redis rejects
writes when it is full instead of deleting queued Celery tasks. Redis holds
only the queues and the task results, which Celery deletes after one day. Its
health command is `redis-cli ping`.

The database password is the podman secret `mmt-db-password`, created once with
`podman secret create mmt-db-password -` from standard input. Both database
units and the app units read it; `env.list` does not contain
`DATABASE_PASSWORD`, so the value exists in one place only.

- `mmt-mariadb` sets `MARIADB_DATABASE=mmt`, `MARIADB_USER=mmt` and
  `MARIADB_RANDOM_ROOT_PASSWORD=1`, takes
  `Secret=mmt-db-password,type=env,target=MARIADB_PASSWORD`, and has
  `HealthCmd=healthcheck.sh --connect --innodb_initialized`.
- `mmt-postgres` sets `POSTGRES_USER=mmt` and `POSTGRES_DB=mmt`, takes
  `Secret=mmt-db-password,type=env,target=POSTGRES_PASSWORD`, runs
  `Exec=postgres -c shared_buffers=2GB`, and has
  `HealthCmd=pg_isready --username=mmt --dbname=mmt`. The database keeps the
  image's default locale.
- The app units take
  `Secret=mmt-db-password,type=env,target=DATABASE_PASSWORD`.

### Image versions

The app, NER and nginx unit files in the repository have no `Image=` line. The
image and its tag are set in the drop-in
`~/.config/containers/systemd/<unit>.container.d/10-image.conf`, which
`deploy/set-version` writes. Redis, MariaDB and PostgreSQL have their image in
the unit file, because their version changes with the repository and not with a
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

With MariaDB (slices 2 and 3), `env.list` contains:

```
DATABASE_ENGINE=mysql
DATABASE_HOST=mmt-mariadb
DATABASE_PORT=3306
DATABASE_NAME=mmt
DATABASE_USER=mmt
CELERY_BROKER_URL=redis://mmt-redis
CELERY_RESULT_BACKEND=redis://mmt-redis
```

From slice 4 on, the first three lines change to:

```
DATABASE_ENGINE=postgresql
DATABASE_HOST=mmt-postgres
DATABASE_PORT=5432
```

`ner.env` contains the two Celery lines. The other variables of `env.list` are
taken over from the old server.

### Row count check

A management command `count_rows` in `mmt/core` prints one line
`app_label.ModelName count` per model, sorted, and leaves out the models
listed under "Data copy to PostgreSQL" as excluded. At each switch-over, its
output on the source database and on the target database must be identical.
The command is removed in slice 5.

### Server move

The new server starts with the same app version that runs on the old server, so
the schema of the dump matches the code. The database is copied with
`mariadb-dump --single-transaction` on the old server and imported with
`podman exec -i mmt-mariadb sh -c 'mariadb -u mmt -p"$MARIADB_PASSWORD" mmt'`
on the new server. Sessions are copied with the database, so users stay logged
in.

The queues in the old Redis are not copied. Before the dump, the web container
on the old server is stopped and the Celery workers process the queues until
`LLEN` of `celery`, `media` and `ner` is 0.

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
  constraints there and emits a system check warning until slice 5. The view
  check applies on both databases.

### Data copy to PostgreSQL

The data is copied with Django's `dumpdata` and `loaddata`, which convert the
types through the ORM. Django creates the schema in PostgreSQL with `migrate`.
The dump excludes `contenttypes`, `auth.permission`, `sessions` and `silk`, and
uses `--natural-foreign --natural-primary`, so that content types and
permissions are matched by name instead of by ID. All users have to log in
again. `loaddata` resets the PostgreSQL sequences itself.

### Backup

`deploy/systemd/mmt-db-backup.service` dumps the database into
`~mmt/backups/db/` and deletes dumps older than 14 days.
`mmt-db-backup.timer` runs it daily at 03:00 with `Persistent=true`.

- With MariaDB: `mariadb-dump --single-transaction` run with `podman exec` in
  `mmt-mariadb`, compressed with gzip into `mmt-YYYY-MM-DD.sql.gz`.
- With PostgreSQL: `pg_dump --format=custom` run with `podman exec` in
  `mmt-postgres`, into `mmt-YYYY-MM-DD.dump`.

## Open decisions

- **TLS certificates.** It is not yet decided how the certificates are
  obtained (ACME in a container or files provided by the university), nor how
  the TLS configuration enters the `mmt-nginx` image without breaking the
  plain-HTTP setup of the dev compose file. Both are written into this spec
  before slice 2 starts.

## File layout

```
app/mmt/core/management/commands/count_rows.py   slices 1–5
app/mmt/transcripts/models.py          JSONArrayLength(Func)
app/mmt/uploaded_files/models.py       unique constraint on Lower('filename'), project
app/mmt/my_account/models.py           unique constraint on Lower('name')
app/mmt/projects/views.py              filename__iexact existence check
.github/workflows/app-tests.yml        matrix over mysql and postgresql
docker/docker-compose.yml, env.list    db service on postgres:18, redis:8
deploy/
  README.md                            describes the Quadlet deployment
  install-units
  set-version COMPONENT TAG
  create-mmt-asr                       unchanged, for the ASR host
  quadlet/                             the units listed above
  systemd/
    mmt-db-backup.service
    mmt-db-backup.timer
```

## Slices

Each slice is deployed on its own.

### Slice 1: Units, scripts and row count

Nothing changes on the old server except the app version.

- [ ] `mmt.network`, the units for web, celery, media, ner, nginx, Redis and
  MariaDB, plus `install-units` and `set-version`.
- [ ] Backup service and timer in the MariaDB form.
- [ ] `count_rows`. Done when a test shows that it lists a model with its row
  count and leaves out the excluded models.
- [ ] `deploy/README.md` describes the Quadlet deployment, the account setup
  and the directories, and no longer describes the `create-*` scripts other than
  `create-mmt-asr`.
- [ ] A release containing `count_rows` runs on the old server.

### Slice 2: Move to the new server

Starts after the open decision on TLS certificates is written into this spec.

- [ ] Prepare the new server: root setup, `env.list`, `ner.env`, the
  `~mmt/user_files` symlink and the secret; `install-units`; `set-version` for
  each component with the versions that run on the old server. Done when all
  units are active and healthy on an empty database.
- [ ] Switch-over, in a maintenance window:
  1. Stop the web container on the old server, wait until the queues are empty,
     stop the workers.
  2. Run `count_rows` and `mariadb-dump` on the old server.
  3. Stop the app units on the new server, drop and recreate the `mmt`
     database in `mmt-mariadb`, import the dump.
  4. Start the units on the new server and run `count_rows` there.
  5. Point the public host name at the new server.
  6. Stop the containers, MariaDB, Redis and nginx on the old server, but leave
     their data in place.

  Done when the outputs of `count_rows` are identical, the app serves a project
  with its files and transcripts over HTTPS, and a waveform job, an NER job and
  a transcription run to completion. The transcription shows that the ASR host
  accepts connections from the new server.
- [ ] The units are active again after a reboot of the new server.
- [ ] A manual start of the backup service writes a dump that `gunzip -t`
  accepts.

Rollback: point the public host name back at the old server and start its
services. Data written on the new server after the switch-over is lost.

### Slice 3: PostgreSQL compatibility

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
- [ ] The dev compose `db` service runs `postgres:18` and the `redis` service
  runs `redis:8`, and `docker/env.list` matches. Done when the dev stack starts
  and migrates.

### Slice 4: PostgreSQL on the new server

- [ ] `mmt-postgres.container`, `mmt-postgres.volume`, the database
  `Requires=`/`After=` lines on the app units changed to `mmt-postgres.service`,
  and the backup service changed to `pg_dump`.
- [ ] Switch-over, in a maintenance window:
  1. Install the units and start `mmt-postgres`.
  2. Stop the app units and `mmt-ner`.
  3. Run `count_rows` and `dumpdata` into `~mmt/migration/` with a one-off
     container of the app image against MariaDB.
  4. Change `env.list` as described under Environment.
  5. Run `loaddata` with a one-off container against PostgreSQL. Its entrypoint
     runs `migrate` first and creates the schema.
  6. Run `count_rows` against PostgreSQL and compare the two outputs.
  7. Start the units. Stop `mmt-mariadb`, but leave its volume in place.

  Done when the outputs of `count_rows` are identical, the app serves a
  project with its files and transcripts, and a manual start of the backup
  service writes a dump that `pg_restore --list` reads.

Rollback: restore the MariaDB lines in `env.list` and the MariaDB dependencies
of the app units, and start `mmt-mariadb`. Data written to PostgreSQL after the
switch-over is lost.

### Slice 5: Cleanup

- [ ] Remove `mysqlclient`, `libmariadb-dev` in `app/Dockerfile`, the `mysql`
  value of `DATABASE_ENGINE`, the `as_mysql` branch of `JSONArrayLength`, the
  MySQL comments in `transcripts/models.py` and the MySQL job in CI.
- [ ] Remove `count_rows`, `~mmt/migration/`, the MariaDB unit and its volume,
  and the replaced `create-*` scripts.
- [ ] Decommission the old server.
