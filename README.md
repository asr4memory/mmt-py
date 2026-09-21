[![App Tests](https://github.com/asr4memory/mmt-py/actions/workflows/app-tests.yml/badge.svg)](https://github.com/asr4memory/mmt-py/actions/workflows/app-tests.yml)
[![App Docker image](https://github.com/asr4memory/mmt-py/actions/workflows/app-docker.yml/badge.svg)](https://github.com/asr4memory/mmt-py/actions/workflows/app-docker.yml)

[![NER Tests](https://github.com/asr4memory/mmt-py/actions/workflows/ner-tests.yml/badge.svg)](https://github.com/asr4memory/mmt-py/actions/workflows/ner-tests.yml)
[![NER Docker image](https://github.com/asr4memory/mmt-py/actions/workflows/ner-docker.yml/badge.svg)](https://github.com/asr4memory/mmt-py/actions/workflows/ner-docker.yml)

[![ASR Tests](https://github.com/asr4memory/mmt-py/actions/workflows/asr-tests.yml/badge.svg)](https://github.com/asr4memory/mmt-py/actions/workflows/asr-tests.yml)
[![ASR Docker image](https://github.com/asr4memory/mmt-py/actions/workflows/asr-docker.yml/badge.svg)](https://github.com/asr4memory/mmt-py/actions/workflows/asr-docker.yml)

# mmt-py

Django version of the Media Management Tool

You can create projects and upload video or audio files for further processing.
In the future, you can create and edit automatic transcriptions based on the
uploaded files.

<p>
  <img src="./images/screenshot.png" alt="screenshot" width="640">
</p>


## Versioning

The app uses date-based versioning (DateVer). A release version is `YYYY.M.D`,
the date of the release, with an optional counter appended for a second release
on the same day, for example `2026.9.14` or `2026.9.14.2`. Releases are made
with `release.sh`, which rejects any other format.

The NER and ASR services are versioned separately from the app and use semantic
versioning (SemVer), for example `0.5.2`.

## Requirements

- Python 3.14
- Node.js 24
- Docker

- Libraries e.g. for Debian:
  - default-libmysqlclient-dev
  - ffmpeg
  - gettext
  - libharfbuzz-subset0
  - libpango-1.0-0
  - libpangoft2-1.0-0
  - pkg-config

## Development

The development environment can be started with uv:

```bash
uv run manage.py runserver
```

In another terminal, start the Vite development server:

```bash
npm run dev
```

Optionally, run the Celery worker with:

```bash
uv run celery -A mmt worker --loglevel=INFO
```

Tests can be run with:

```bash
uv run pytest
```

## Load testing

`locustfile.py` defines a load test that requests the welcome page. Run it
against a deployment with:

```bash
uv run locust -H https://example.org -u 20 -r 2 -t 5m
```

`-u` is the number of concurrent users, `-r` the number of users started per
second and `-t` the duration. The web interface is served at
http://localhost:8089; `--headless` prints the statistics to the terminal
instead.
