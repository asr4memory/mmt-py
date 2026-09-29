# Synchronous application under gunicorn

This is an executable spec. It is the authoritative record of the decisions for
running the Django application as a WSGI application under gunicorn instead of
an ASGI application under uvicorn. An implementing session works from this
document and resolves ambiguity by reading it.

## Motivation

Every view, middleware and API operation in the application is synchronous.
The production image nevertheless runs `uvicorn --workers 4 mmt.asgi:application`
([`app/Dockerfile`](../app/Dockerfile)), so Django's ASGI handler passes every
request from the event loop to a thread through `sync_to_async` and the
response back again. The only code that uses the event loop is the file
streaming in [`core/file_serving.py`](../app/mmt/core/file_serving.py) and
`file_data` in [`core/utils.py`](../app/mmt/core/utils.py). Those iterators are
asynchronous only because Django under ASGI reads a synchronous response
iterator completely into memory before it sends the first byte.

The asynchronous code has further costs: tests read response bodies through
`asyncio.run`
([`core/streaming_test_helpers.py`](../app/mmt/core/streaming_test_helpers.py)),
models carry unused async variants of their path properties, and the
development server (`manage.py runserver`, WSGI) runs the application under a
different protocol than production does.

Under gunicorn with the `gthread` worker class, 4 processes with 8 threads each
handle up to 32 requests concurrently, each request runs in one thread from
start to end, and development and production both run WSGI.

## Non-goals

- **The ASR and NER services are not changed.** They are FastAPI applications
  and stay under uvicorn.
- **No gunicorn configuration file.** The settings are command-line options in
  the `CMD` of the image.
- **No persistent database connections.** `CONN_MAX_AGE` stays at its default
  of 0. With 32 threads, each thread opens at most one connection per request,
  which is within MariaDB's default `max_connections` of 151 together with the
  Celery workers.
- **No worker recycling.** `--max-requests` is not set.
- **No change to the memory or CPU limits** of the web container.
- **No migration of `download_download` and `download_dpa` to `serve_file`.**
  That is slice 3 of
  [`2026-09-07-x-accel-redirect.md`](2026-09-07-x-accel-redirect.md). This spec
  only makes `file_data` synchronous.

## Feature reference

### Deployments

Whether production runs the nginx container is not decided. The application
has to work in both of these deployments, and every decision below states which
of them it concerns.

- **With nginx.** The `mmt-nginx` container is in front of the web container
  and `X_ACCEL_LOCATION` is set. nginx serves the media files, reads each
  upstream response into its own buffers, and a request thread is held only for
  the time Django needs to produce the response.
- **Without nginx.** The web container is published directly, or behind a TLS
  terminator whose buffering behavior is not known, and `X_ACCEL_LOCATION` is
  empty. The spec assumes that nothing in front of gunicorn buffers request or
  response bodies. Every media response, download and upload chunk is then
  transferred by a gunicorn thread, and the thread is held until the last byte
  has been written to the socket or read from it. Idle keep-alive connections
  do not hold a thread: the `gthread` worker waits for them in its main thread.

In the deployment without nginx, the 32 threads are therefore also the limit on
concurrent transfers. Under uvicorn a transfer did not hold a thread between
chunk reads. This limit is accepted. Two measures keep the time a transfer
holds a thread short where it is possible:

- An open-ended range is served in bounded parts (see "Open-ended ranges").
  This covers media playback, which is the transfer that stays open longest.
- A download without a `Range` header, such as the download of an original
  file or of a file from the download directory, holds a thread for the whole
  download. No measure applies to it.
- An upload chunk holds a thread for its transfer. A chunk is at most 10 MB, so
  the time is bounded by the client's upload rate.

### Server command

The `CMD` in [`app/Dockerfile`](../app/Dockerfile) becomes:

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "gthread", "--threads", "8", "--access-logfile", "-", "--log-level", "info", "mmt.wsgi:application"]
```

- `--worker-class gthread` is written out although gunicorn selects it for any
  `--threads` value above 1, so the command states the model it depends on.
- `--access-logfile -` writes the access log to standard output. uvicorn writes
  an access log by default and gunicorn does not, so without the option the
  container logs would lose the request lines.
- `--timeout` keeps its default of 30 seconds. For the `gthread` worker the
  timeout applies to the heartbeat of the worker process, which the main thread
  sends while request threads run, so a request that takes longer than 30
  seconds is not terminated.
- `--forwarded-allow-ips` is not set. Django reads `X-Forwarded-Proto` itself
  through `SECURE_PROXY_SSL_HEADER`, which does not depend on the server.
- The port stays 8000, so the health check (`nc -vz -w 2 localhost 8000`), the
  deploy script and the nginx upstream do not change.

### Dependencies

[`app/pyproject.toml`](../app/pyproject.toml): `gunicorn` is added with `uv add`
and written with `~=` on the minor version, like the other entries. `uvicorn`
and `aiofiles` are removed. [`app/mmt/asgi.py`](../app/mmt/asgi.py) is deleted;
`WSGI_APPLICATION = 'mmt.wsgi.application'` in the settings is already present.

### Synchronous response iterators

Under WSGI the relation between the two iterator kinds is the reverse of the
one under ASGI: Django sends a synchronous iterator chunk by chunk, and consumes
an asynchronous iterator through `async_to_sync`, which reads it completely into
memory and emits a warning. Both iterators therefore become plain generators.

`_file_range_iterator` in `core/file_serving.py`:

```python
def _file_range_iterator(file_path, start, length, chunk_size=CHUNK_SIZE):
    """Yield `length` bytes from `file_path` starting at byte offset `start`."""
    with open(file_path, 'rb') as f:
        f.seek(start)
        remaining = length
        while remaining > 0:
            chunk = f.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
```

The comment on `CHUNK_SIZE` loses its reference to thread hops and keeps the
statement that the memory held per response is one chunk. The docstring of
`serve_file` says the body is an iterator that reads `chunk_size` bytes at a
time, without "asynchronous".

`file_data` in `core/utils.py`:

```python
def file_data(file_path, chunk_size=65536):
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            yield chunk
```

The unused `teller` counter is removed with the rewrite.

A client disconnect closes the file as follows: gunicorn calls `close()` on the
response, Django's `StreamingHttpResponse` calls `close()` on the generator,
and the `with` block closes the file.

### Open-ended ranges

This concerns the direct path of `serve_file`, which is the path of the
deployment without nginx. With nginx, `serve_file` returns before it reads the
`Range` header.

A browser media element requests `Range: bytes=0-` and, after a seek,
`bytes=N-`. It reads the response only as fast as it plays, so a response that
covers the rest of the file keeps the connection, and under gunicorn the
thread, busy until playback ends or the tab is closed. A range with a first
byte and no last byte is therefore answered with at most
`OPEN_RANGE_LIMIT` bytes:

```python
# Eight megabytes. An open-ended range is answered with at most this many
# bytes, so a media element that reads at playback speed holds a request
# thread only for the transfer of one part.
OPEN_RANGE_LIMIT = 8 * 1024 * 1024
```

- `serve_file` gains the keyword parameter `open_range_limit=OPEN_RANGE_LIMIT`,
  next to `chunk_size`, so tests can use a small limit.
- For `bytes=N-`, `end` is `min(N + open_range_limit - 1, file_size - 1)`. The
  response is the usual `206` with `Content-Range: bytes N-end/size`. The media
  element reads `Content-Range` and requests the next part with `bytes=end+1-`
  when it needs it.
- A closed range `bytes=a-b` is served in full, as before. A client that names
  the last byte expects exactly that range.
- A suffix range `bytes=-n` is served in full, as before. It asks for the end of
  the file and is used for small reads such as container metadata.
- A request without a `Range` header, or one whose range is ignored because of
  `If-Range`, is answered with `200` and the whole file, as before.

The limit works under uvicorn as well as under gunicorn, so
it is its own slice and ships before the server change.

### Tests of the streamed body

`streamed_body` and `core/streaming_test_helpers.py` are deleted. Tests read a
streamed body with `response.getvalue()`, which `StreamingHttpResponse`
provides for synchronous iterators.

In [`core/tests/test_file_serving.py`](../app/mmt/core/tests/test_file_serving.py):

- `test_the_streamed_body_is_an_asynchronous_iterator` becomes
  `test_the_streamed_body_is_a_synchronous_iterator` and asserts
  `not response.is_async`. Its docstring states that under WSGI an asynchronous
  iterator is read completely into memory before the first byte is sent.
- `test_the_body_is_read_in_chunks_of_the_given_size` asserts
  `list(response.streaming_content) == [b'123', b'456', b'78']`.
- `test_stopping_the_iteration_closes_the_file` reads one part with
  `next(response.streaming_content)`, then calls `response.close()`, which is
  the call the WSGI server makes, and asserts that the one opened file is
  closed.

### Removed async model members

`Project.aproject_directory`, `Project.aupload_directory` and
`UploadedFile.afile_path` have no callers and are deleted. They exist for
async views, and there are none.

### Request buffering for upload chunks

This concerns only the deployment with nginx. Without nginx, nothing in front
of gunicorn can buffer the chunk, and the thread is held for the transfer as
described in "Deployments".

[`nginx/default.conf.template`](../nginx/default.conf.template) sets
`proxy_request_buffering off` for all locations. nginx then opens the upstream
connection when the request starts and forwards the body at the speed of the
client. Under uvicorn the body was read by the event loop without holding a
thread. Under gunicorn the thread that handles the request is held for the
whole transfer: a 10 MB chunk over a 1 Mbit/s uplink holds a thread for about
80 seconds, and 32 such uploads at once hold every thread.

A location for the chunk route turns buffering on:

```nginx
location ~ ^/uploaded-files/\d+/upload/\d+/$ {
    proxy_request_buffering on;
    proxy_pass http://${MMT_WEB_UPSTREAM};
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

nginx writes the chunk to its temporary directory in the nginx container and
opens the upstream connection only after the client has sent the whole body.
A chunk is at most `MMT_UPLOAD_CHUNK_SIZE` (10 MB), so the space used per
concurrent upload is bounded. `client_max_body_size 0` at the server level
applies to this location as well. `proxy_request_buffering off` stays for all
other locations. The comment above it no longer mentions a non-chunked upload
path, since all uploads go through the chunk route. `nginx/VERSION` is
increased so that a new image tag is published.

### Long-lived responses

A request under gunicorn holds one of 32 threads until its response is
complete. A response that stays open, such as a server-sent event stream, holds
a thread for as long as the client keeps it open, and 32 open browser tabs
stop the application from answering other requests. After this change the
application has no response that stays open longer than the time needed to
produce it, and a later feature must not add one.

### Documentation

- [`docs/api-architecture.md`](../docs/api-architecture.md), section
  "Synchronous now": the paragraph states that the application runs under
  gunicorn as a WSGI application and has no async code paths, and drops the
  statement that routers could be switched to `async def` later.
- [`deploy/README.md`](../deploy/README.md): the row for `create-mmt-app-web`
  names gunicorn with 4 processes and 8 threads each. A paragraph states that
  without the nginx container every media transfer, download and upload chunk
  holds one of the 32 threads while it is in progress.

### Relation to other specs

Two specs that are not yet implemented depend on the ASGI stack and have to be
revised before they are implemented. Revising them is a separate change, not
part of this spec.

- [`2026-09-18-asr-completion-notifications.md`](2026-09-18-asr-completion-notifications.md)
  delivers events through a server-sent event stream that stays open for the
  lifetime of a page, which the section "Long-lived responses" excludes.
- [`2026-07-15-download-all-as-zip.md`](2026-07-15-download-all-as-zip.md)
  builds the archive in an asynchronous generator with `aiofiles`,
  `pytest-asyncio` and `AsyncClient`. Under WSGI the generator is synchronous
  and none of the three is needed.

## File layout

```
app/Dockerfile                          CMD runs gunicorn
app/pyproject.toml, app/uv.lock         + gunicorn, - uvicorn, - aiofiles
app/mmt/asgi.py                         deleted
app/mmt/core/file_serving.py            _file_range_iterator is a generator,
                                        OPEN_RANGE_LIMIT, open_range_limit
app/mmt/core/utils.py                   file_data is a generator
app/mmt/core/streaming_test_helpers.py  deleted
app/mmt/projects/models.py              - aproject_directory, - aupload_directory
app/mmt/uploaded_files/models.py        - afile_path
nginx/default.conf.template             buffered location for upload chunks
nginx/VERSION                           increased
docs/api-architecture.md                "Synchronous now" rewritten
deploy/README.md                        web container row
```

## Slices and tasks

Slice 2 changes the server and the iterators together. Either change alone
makes Django read every streamed body completely into memory: a synchronous
iterator under uvicorn, or an asynchronous iterator under gunicorn.

Each slice that is checked against the compose stack is checked in both
deployments. "Without nginx" means the `web` service reached directly on a
published port, for example `8001:8000` added in a local compose override file
that is not committed, with `X_ACCEL_LOCATION` removed from `env.list`.

- [ ] **1 Bounded open-ended ranges.** Tests first in
  `core/tests/test_file_serving.py`, with a 10-byte file and
  `open_range_limit=4`: `bytes=2-` answers `206` with `Content-Range: bytes
  2-5/10` and the body `2345`; `bytes=8-` answers `bytes 8-9/10`; `bytes=2-8`
  answers the full closed range; `bytes=-6` answers the last six bytes; a
  request without `Range` answers `200` with all ten bytes. Then add
  `OPEN_RANGE_LIMIT` and the parameter. Done when `uv run pytest` passes and,
  without nginx, `curl -H 'Range: bytes=0-'` on the stream URL of a video
  larger than 8 MB returns `206` with `Content-Range: bytes 0-8388607/<size>`,
  and the video plays and seeks to its end in Firefox and in Chromium.
- [ ] **2 gunicorn and synchronous iterators.** Change the three tests in
  `test_file_serving.py` as described, replace every `streamed_body(response)`
  with `response.getvalue()` and delete the helper module, then rewrite
  `_file_range_iterator` and `file_data`, add `gunicorn` and change the `CMD`.
  Done when `uv run pytest` passes with no `StreamingHttpResponse` warning in
  its output, and against the compose stack: the container log shows gunicorn
  starting 4 workers and access lines for requests; in both deployments a
  logged in page loads, a video plays and seeks, `curl -r 100-199` on a stream
  URL returns `206` with 100 bytes, a file from the download directory
  downloads completely, and a chunked upload of a file of several hundred
  megabytes succeeds; and a locust run with `app/locustfile.py` against each
  deployment reports no failures.
- [ ] **3 Buffered upload chunks.** Add the nginx location, update the comment
  and increase `nginx/VERSION`. Done when, with nginx, a chunk `POST` sent with
  `curl --limit-rate 50k` shows no established connection to port 8000 in the
  web container (`ss -tn`) while curl is still sending, the chunk is stored
  once curl finishes, and an upload through the browser succeeds in both
  deployments.
- [ ] **4 Removal of the async remnants.** Delete `asgi.py` and the three async
  model members, remove `uvicorn` and `aiofiles` from the dependencies, update
  `docs/api-architecture.md` and `deploy/README.md`. Done when
  `grep -rnE "async def|await |asyncio|aiofiles|uvicorn|asgi" app/mmt` returns
  nothing, `uv run pytest` passes and the image builds.
