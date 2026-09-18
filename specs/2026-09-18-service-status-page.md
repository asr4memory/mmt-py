# Service status page for staff

This is an executable spec. It is the authoritative record of the decisions for
showing the health of the ASR and NER services inside the Django application. An
implementing session works from this document and resolves ambiguity by reading
it.

## Motivation

The ASR and NER services each expose a `GET /health` endpoint that reports
`status` and `version` ([`asr/api.py`](../asr/api.py),
[`ner/api.py`](../ner/api.py)), but the application never calls it. When
transcription or entity extraction stops working, the only way to tell whether a
service is reachable is to log into the host. Staff need one page that answers
the question, and the answer must not be produced by a blocking HTTP call inside
a page request.

## Non-goals

- **Nothing user-facing.** Regular users see no service status. What a user
  needs to know about an unavailable service belongs to the transcription
  workflow (a disabled action, a job error) and is not part of this feature.
- **No liveness beyond the process.** `GET /health` on the ASR service returns
  as soon as the process serves requests and says nothing about the worker, the
  spool or the model cache. The page reports exactly that, and does not probe
  queue depth, GPU state or model availability.
- **No history and no alerting.** Only the most recent reading is stored. No
  model, no migration, no email, no Sentry event when a service is down.
- **No status for the other infrastructure.** MySQL, Redis and the Celery
  workers are out of scope; a failing Celery beat is visible as a stale
  timestamp on the page.

## Feature reference

### Cache backend

The last reading is shared state between the Celery worker that writes it and
the gunicorn worker that reads it, so the local-memory default is not usable.
[`settings.py`](../app/mmt/settings.py) gains a `CACHE_URL` entry in the
`environ.Env` defaults, `(str, 'locmemcache://')`, and:

```python
CACHES = {'default': env.cache('CACHE_URL')}
```

`docker/env.list` sets `CACHE_URL=redis://redis/1`, a different database from
the Celery broker on the same Redis instance. Development and test keep the
local-memory default, which is per-process but sufficient because the poll task
runs eagerly or not at all.

### The reading

[`core/tasks.py`](../app/mmt/core/tasks.py) holds the key, the poll task and the
reader:

```python
SERVICE_HEALTH_CACHE_KEY = 'service_health'
SERVICE_HEALTH_TIMEOUT = 5
SERVICE_HEALTH_TTL = 900


@shared_task
def task_poll_service_health() -> None:
    """Record the health of the ASR and NER services in the cache."""


def read_service_health() -> dict:
    """The most recent reading, or an empty dict when there is none."""
```

The task requests `GET {base_url}/health` for each configured service with a
timeout of `SERVICE_HEALTH_TIMEOUT` seconds and writes one dict under
`SERVICE_HEALTH_CACHE_KEY` with a TTL of `SERVICE_HEALTH_TTL` seconds:

```python
{
    'checked_at': '2026-09-18T10:00:00+00:00',
    'services': {
        'asr': {'ok': True, 'version': '0.4.0', 'error': None},
        'ner': {'ok': False, 'version': None, 'error': 'Connection refused'},
    },
}
```

`checked_at` is `timezone.now().isoformat()`. A service whose base URL is empty
is absent from `services`; this is the case for ASR when `ASR_API_URL` is unset,
which [`settings.py`](../app/mmt/settings.py) already treats as the feature
being disabled. A non-2xx response or a `requests.RequestException` yields
`ok: False` with the exception text in `error`, truncated to 200 characters. The
task never raises: one unreachable service must not prevent the other from being
recorded.

The TTL is longer than the polling interval, so a single missed tick leaves the
previous reading in place and the page shows its age rather than nothing.

### Polling interval

`CELERY_BEAT_SCHEDULE` gains:

```python
'poll-service-health': {
    'task': 'mmt.core.tasks.task_poll_service_health',
    'schedule': 300.0,
},
```

### The page

[`core/views.py`](../app/mmt/core/views.py) gains:

```python
@staff_member_required
@require_GET
def service_status(request):
```

It puts `read_service_health()` into the context and renders
`core/service_status.html`, which extends `admin/base_site.html` so the page
carries the admin styling and navigation. [`urls.py`](../app/mmt/urls.py)
routes it at `admin/service-status/`, placed before `admin/` so the pattern
matches first, under the name `service_status`.

The template renders one row per service with its name, a state, the version and
the error text when there is one. The state is one of three:

| Condition | Displayed as |
| --- | --- |
| `ok` is true | Available |
| `ok` is false | Unavailable, with the error text |
| the service is absent from `services` | Not configured |

Above the rows the page states when the reading was taken, as
`{{ checked_at }}` rendered with `timesince`. An empty reading renders the
sentence "No reading yet." instead of the rows, which is what a stopped Celery
beat or a cold cache looks like.

The upload activity line currently rendered by `recent_upload_activity` in
[`admin/index.html`](../app/mmt/templates/admin/index.html) moves to this page as
a further row, and the admin index instead links to the page.

### Translations

Every string on the page and the link label are translatable and get German
translations in `locale/de/LC_MESSAGES/django.po`: Service status, Service,
State, Version, Available, Unavailable, Not configured, No reading yet, and the
sentence naming the age of the reading.

### Pinned decisions

- **The page is not registered on the `AdminSite`.** A plain view under the
  `admin/` path prefix with `@staff_member_required` and a template extending
  `admin/base_site.html` gives the same authentication and appearance without
  subclassing `AdminSite` or overriding `get_urls`.
- **Staff, not superuser.** `staff_member_required` matches the existing
  `trigger_error` view and the admin itself.
- **The reading is a plain dict, not a model.** Only the latest value matters,
  so a cache entry with a TTL expresses the lifetime directly and needs no
  migration and no cleanup.
- **Both services are polled in one task.** The number of tasks stays fixed and
  the page shows one consistent `checked_at` for both readings.

## Slices and tasks

- [ ] **1 Cache backend and the poll task.** Add `CACHE_URL` and `CACHES` to
  the settings and to `docker/env.list`, add `SERVICE_HEALTH_CACHE_KEY`,
  `task_poll_service_health` and `read_service_health` to `core/tasks.py`, and
  register the beat entry. Done when `core/tests/test_tasks.py` asserts, with
  the HTTP call patched, that a successful response is recorded as `ok: True`
  with the reported version, that a `requests.RequestException` is recorded as
  `ok: False` with the error text while the other service is still recorded,
  that a service with an empty base URL is absent from `services`, and that
  `read_service_health()` returns `{}` when nothing has been written.
- [ ] **2 The status page.** Add the view, the URL, the template and the German
  translations, move the upload activity line off the admin index and link to
  the page from it. Done when `core/tests/test_views.py` asserts that an
  anonymous user and a non-staff user are redirected, that a staff user sees
  both service names and the version of an available service from a reading put
  into the cache by the test, that an unavailable service shows its error text,
  and that an empty cache renders the "No reading yet" sentence.
