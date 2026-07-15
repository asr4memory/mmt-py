# Spec: Download all project files as a zip

Status: not started.

This document is an **executable spec** (spec-driven development): it is the
prompt an implementing session works from and the authoritative record of every
decision, not a background sketch. Resolve ambiguity by reading this doc, not by
inventing; if a genuinely new decision comes up, write it into the doc as part
of the task. Check off tasks (`[x]`, with date) as they land. Do not duplicate
CLAUDE.md conventions here (test-first, pytest style, CSS units, translations in
both locales).

## Motivation

The project detail page lists the project's downloadable files, each with its
own download link ([`download_download`](../app/mmt/projects/views.py) streams a
single file). A user who wants everything currently downloads file by file.
A single "Download all" action that streams every downloadable file as one zip
archive removes that repetition.

The download directory usually holds small transcript files, but sometimes a
large transcript and occasionally a processed audio or video file. File sizes
are effectively unbounded, so the archive must never be fully held in memory or
staged on disk. This drives the streaming decision below.

## Non-goals (v1)

Do not add these, even where they would be easy:

- **No selection.** The archive always contains every file in the download
  directory; there is no per-file checkbox or subset download.
- **No new runtime dependency.** The Python standard library `zipfile` streams to
  a non-seekable object; `zipstream-ng` and similar are not added. This is about
  what ships: the feature does add `pytest-asyncio` to the `dev` dependency
  group, because the helper is an async generator and the suite has no way to run
  an `async def` test without it (see Tests).
- **No progress bar / Content-Length.** A streamed zip has unknown length; the
  response sends no `Content-Length` and the browser shows no progress.
- **No nested directories.** The download directory is flat
  ([`get_dir_contents`](../app/mmt/projects/utils.py) filters to files); the
  archive is flat, file names only.
- **No caching or persisting the archive.** It is generated per request and
  discarded.

## Feature reference

### Route

| method & path | name | success | errors |
|---|---|---|---|
| `GET /projects/<int:pk>/downloads/download-all/` | `projects:download-all` | `200` streamed zip | `404` project not owned by the requester; `404` when the download directory contains no files; `500` when the download directory does not exist |

Ownership is enforced exactly as the sibling views do:
`get_object_or_404(Project, pk=pk, user=request.user)`. The view is
`@require_GET` and `@login_required`, mirroring
[`download_download`](../app/mmt/projects/views.py).

The URL is registered **before** the `<str:filename>` download routes: place it
above the two `downloads/<str:filename>/` patterns in
[`urls.py`](../app/mmt/projects/urls.py) so the literal segment `download-all`
is matched as its own route and never captured as a `filename`. Django tries the
patterns in order, so registering it after them would send
`/projects/1/downloads/download-all/` to
[`download_detail`](../app/mmt/projects/views.py) with `filename='download-all'`,
which would return `404` because no such file exists.

### Response

- `Content-Type: application/zip`
- `Content-Disposition: attachment; filename="<archive-name>.zip"`
- Body is a `StreamingHttpResponse` whose iterator yields zip bytes as they are
  produced.

### Decided conventions

- **Archive file name:** `f'{filename_safe(project.title)}.zip'` — the safe title
  only, without the date suffix. [`filename_safe`](../app/mmt/core/utils.py)
  produces an ASCII-safe, lowercased name and is the same function
  [`directory_name`](../app/mmt/projects/models.py) builds on; the project title
  is validated (`validate_filename_safe`), so the result is never empty. The date
  suffix that `directory_name` appends is omitted so the download is named after
  the project rather than its internal directory.
- **Member names inside the archive:** the plain file name, passed as
  `arcname=path.name`, no directory prefix. Order follows
  [`get_dir_contents`](../app/mmt/projects/utils.py), i.e. case-insensitive by
  name.
- **Compression:** `zipfile.ZIP_DEFLATED`. The archive is always compressed. The
  large majority of files in the download directory are text transcripts, which
  compress well, so deflating meaningfully reduces the archive size. The
  occasional already-compressed audio or video file gains little from deflation,
  but it is not special-cased; the same compression choice for every member keeps
  the helper simple.
- **Empty download directory → `404`.** Determined by
  `get_dir_contents(project.download_directory)` returning an empty list. The
  "Download all" button is hidden in the template in this case (see task 3), so
  the `404` only guards direct URL access.
- **Missing download directory → `500`.** `get_dir_contents` raises
  `FileNotFoundError` when the directory does not exist. That is not a client
  error: every project is created with its download directory
  ([`ensure_directories`](../app/mmt/projects/models.py)), so its absence is a
  broken server-side invariant, not a request for something that was never
  there. The view catches `FileNotFoundError`, logs it with
  `logger.error(..., exc_info=True)` naming the project pk and the path, and
  returns `HttpResponseServerError('Download directory does not exist.')`. The
  plain-text body follows the sibling download views, which return
  `HttpResponseNotFound('File does not exist.')` rather than a rendered page;
  [`project_detail`](../app/mmt/projects/views.py) renders
  `project_detail_error.html` instead because it is a page request, and a
  download endpoint is not.
- **Each member is opened with a `ZipInfo`, not a name:**

  ```python
  zinfo = zipfile.ZipInfo.from_file(path, arcname=path.name)
  zinfo.compress_type = zipfile.ZIP_DEFLATED
  with archive.open(zinfo, 'w') as dest:
  ```

  This is required for ZIP64, and it is why the archive supports the unbounded
  file sizes the Motivation describes. Passing a `str` member name instead makes
  `zipfile` build a `ZipInfo` whose `file_size` is `0`; its local header is then
  written with 32-bit size fields, and a member that turns out to exceed
  `ZIP64_LIMIT` (2 GiB) makes `_ZipWriteFile.close` raise
  `RuntimeError('File size too large, try using force_zip64')` after the `200`
  and the headers have already been sent, so the client would receive a truncated
  archive rather than an error. `ZipInfo.from_file` stats the file, so
  `file_size` is known before the first read and `_open_to_write` computes
  `zip64 = force_zip64 or (zinfo.file_size * 1.05 > ZIP64_LIMIT)` correctly per
  member: small transcripts keep compact 32-bit headers and a large media file
  gets ZIP64 automatically. The `1.05` factor covers compression expansion.
  `force_zip64=True` is deliberately **not** used: it would pay 28 bytes on every
  member to solve a problem almost no member has. Nothing further is needed for
  large archives, because `_write_end_record` already moves sizes and header
  offsets into a per-entry ZIP64 extra field and writes the ZIP64
  end-of-central-directory record when the central directory offset exceeds the
  same limit, both gated on `allowZip64`, which defaults to `True`.

  **Setting `compress_type` on the `ZipInfo` is not optional.**
  `ZipFile.open` applies the archive-wide `self.compression` only when the member
  is named by a `str`; given a `ZipInfo` it uses that object's own
  `compress_type`, which `from_file` defaults to `ZIP_STORED`. Omitting the
  assignment produces a valid, round-tripping, **uncompressed** archive, silently
  contradicting the Compression decision above.
  `test_zip_stream_uses_deflate` is what catches this.
- **Member timestamps:** the source file's mtime, which
  `ZipInfo.from_file` reads. Extracted files therefore keep the date the
  processing step produced them rather than the date of the download.
- **Read chunk size:** `65536`, matching
  [`file_data`](../app/mmt/core/utils.py).

### Streaming zip mechanism (verified)

`zipfile.ZipFile` writes to any object exposing `write` and `flush`. When that
object does not expose `seek`/`tell`, `ZipFile` treats the output as
non-seekable and emits data descriptors, so a valid archive is produced without
ever seeking backwards. That is exactly what a streaming HTTP response needs.

Verified on this repo's interpreter: writing two members through such an object
with `ZIP_DEFLATED` yields an archive that re-opens cleanly and passes
`testzip()`. The write-only sink must implement both `write(data)` and a no-op
`flush()` (`ZipFile.close` calls `flush`).

`zip_stream` is an **async generator**, matching the existing single-file
download [`file_data`](../app/mmt/core/utils.py). This is required, not
optional: the app is served over ASGI (uvicorn, see the assumption below), and
under Django 6.0 a `StreamingHttpResponse` built from a synchronous iterator is
consumed with `sync_to_async(list)(...)`, which reads the whole archive into a
list in memory before sending any bytes. That both defeats streaming and
violates the memory bound in the motivation. An async iterator is streamed chunk
by chunk instead.

Consequences of the async generator:

- File reads use `aiofiles.open(...)` and `await src.read(chunk_size)`, so each
  read is a suspension point at which the event loop runs other requests handled
  by the same worker. A single download therefore does not occupy the worker for
  its whole duration.
- `zipfile` itself is synchronous. Compressing one chunk (`dest.write(data)`)
  runs on the event loop thread, but a 64 KB chunk compresses in about a
  millisecond, and the awaited read between chunks returns control to the loop.
  There is no long synchronous stretch.

Reference implementation sketch (not prescriptive beyond the decided
conventions):

```python
class _Sink:
    def __init__(self):
        self._buf = bytearray()
    def write(self, data):
        self._buf += data
        return len(data)
    def flush(self):
        pass
    def take(self) -> bytes:
        chunk = bytes(self._buf)
        self._buf.clear()
        return chunk


async def zip_stream(files: list[Path], chunk_size: int = 65536):
    sink = _Sink()
    with zipfile.ZipFile(sink, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            zinfo = zipfile.ZipInfo.from_file(path, arcname=path.name)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            with archive.open(zinfo, 'w') as dest:
                async with aiofiles.open(path, 'rb') as src:
                    while data := await src.read(chunk_size):
                        dest.write(data)
                        if chunk := sink.take():
                            yield chunk
            if chunk := sink.take():
                yield chunk
    if chunk := sink.take():
        yield chunk
```

`archive.open(zinfo, 'w')` for member writing and streaming to a non-seekable
sink are standard-library `zipfile` features. `aiofiles` is already a project
dependency (used by [`file_data`](../app/mmt/core/utils.py)), so the async
reads add no new dependency.

## File layout

- **[`app/mmt/projects/utils.py`](../app/mmt/projects/utils.py)** — new helper
  `zip_stream(files, chunk_size=65536)` (async generator yielding zip bytes) plus
  the private `_Sink`. Placed here beside
  [`get_dir_contents`](../app/mmt/projects/utils.py) so it is unit-testable
  without HTTP.
- **[`app/mmt/projects/views.py`](../app/mmt/projects/views.py)** — new view
  `download_all(request, pk)` mirroring `download_download`.
- **[`app/mmt/projects/urls.py`](../app/mmt/projects/urls.py)** — new
  `download-all` route, listed before the `<str:filename>` routes.
- **[`app/mmt/projects/templates/projects/project_detail.html`](../app/mmt/projects/templates/projects/project_detail.html)**
  — the "Download all" button in the "Downloadable files" section, shown only
  when there are files.
- **Tests:** `app/mmt/projects/tests/test_utils.py` (helper) and a **new**
  `app/mmt/projects/tests/test_downloads.py` (view and button). The new file is
  used rather than `test_views.py` because that file is already 724 lines and 55
  tests, and has no download tests to sit beside. `test_downloads.py` covers the
  downloads area of the projects app, so the currently untested `download_detail`
  and `download_download` views have a home to move into later.
- **[`app/pyproject.toml`](../app/pyproject.toml)** — `pytest-asyncio~=1.4` added
  to the `dev` dependency group. It is not in the suite today, so without it an
  `async def` test is collected but never awaited. Verified against this repo's
  pinned pytest 9.1 and pytest-django 4.12: `async def` tests run with
  `@pytest.mark.django_db`, with the async ORM and with `AsyncClient`. No
  `asyncio_mode` setting is added; the default strict mode is kept, so every
  async test carries an explicit `@pytest.mark.asyncio`.

Key signature the tests target:

```python
# utils.py
async def zip_stream(files: list[Path], chunk_size: int = 65536) -> AsyncIterator[bytes]
```

## Tests

The full list of tests this feature adds. Helper tests pass a small explicit
`chunk_size` instead of building files over the 65536-byte default.

**How the async generator is consumed.** `zip_stream` is an async generator, so
every test in `test_utils.py` is `async def` with `@pytest.mark.asyncio` and
collects it directly:

```python
chunks = [chunk async for chunk in zip_stream(files, chunk_size=32)]
```

Collect into a list and join where whole-archive bytes are needed; do not collect
straight into joined bytes, because
`test_zip_stream_never_holds_whole_archive_in_memory` asserts on the largest
individual chunk.

The view tests are **not** async, with one exception. Five of the six check only
the status and the headers and never read the body, which the ordinary sync
`client` fixture handles without complaint, so they stay sync like every other
view test in the suite. Only
`test_download_all_archive_contains_every_file` reads the body, and it uses
`django.test.AsyncClient` in an `async def` test:

```python
response = await AsyncClient().get(url)
chunks = [chunk async for chunk in response.streaming_content]
```

Do not read the body from the sync client instead. `b''.join(response)` does
return the bytes, but it emits Django's warning `"StreamingHttpResponse must
consume asynchronous iterators in order to serve them synchronously"` and routes
through `sync_to_async(list)`, which buffers the whole archive — the exact
behavior the streaming zip mechanism section rejects, in the one test that reads
an entire archive. `b''.join(response.streaming_content)`, the pattern used by
`mmt/uploaded_files/tests/test_views.py`, raises `TypeError` here; those tests
work only because `_file_range_iterator` in
[`file_serving.py`](../app/mmt/core/file_serving.py) is a synchronous generator.

**Why `test_zip_stream_never_holds_whole_archive_in_memory` uses random bytes.**
DEFLATE returns no output until its internal buffer fills, so compressible
content is not emitted during the read loop at all; it arrives in one burst when
the member is flushed. Measured: 5.4 MB of repeating text yields output on only 2
of 83 reads, because the whole archive is about 10 KB. Against such content an
implementation that buffered everything would still produce only small chunks and
would pass the test. Incompressible content removes that: 5 MB of `os.urandom`
yields output on all 77 reads, with the largest chunk at 65601 bytes for a 65536
`chunk_size`, so buffering the archive becomes visible as an oversized chunk. Do
not replace the random content with text.

### `app/mmt/projects/tests/test_utils.py` — `zip_stream`

- **`test_zip_stream_namelist_matches_input_order`** — joining the yielded chunks
  re-opens as a zip whose `namelist()` equals the input file names, in the order
  given.
- **`test_zip_stream_members_round_trip`** — every member decompresses back to the
  exact bytes of its source file.
- **`test_zip_stream_member_spanning_multiple_chunks_round_trips`** — a file
  larger than `chunk_size` round trips unchanged, exercising the repeated-read
  loop and DEFLATE's internal buffering.
- **`test_zip_stream_zero_byte_member`** — a zero-byte file appears in
  `namelist()` and round trips as `b''`.
- **`test_zip_stream_archive_passes_testzip`** — `testzip()` returns `None`, i.e.
  no member is corrupt and every CRC matches.
- **`test_zip_stream_uses_deflate`** — every `ZipInfo.compress_type` equals
  `zipfile.ZIP_DEFLATED`.
- **`test_zip_stream_preserves_member_mtime`** — each member's
  `ZipInfo.date_time` equals the source file's mtime (`os.utime` one of the
  fixture files to a fixed past timestamp, then compare against
  `time.localtime(path.stat().st_mtime)[:6]`; zip stores local time to
  two-second resolution). This is the observable consequence of opening members
  with a `ZipInfo` from `from_file` rather than a plain name, which is also what
  makes the ZIP64 decision work. The 2 GiB path itself is not tested: a fixture
  that large would still have to be read and deflated even as a sparse file.
- **`test_zip_stream_empty_file_list`** — an empty `files` list still yields a
  valid archive with `namelist() == []`.
- **`test_zip_stream_never_holds_whole_archive_in_memory`** — the memory bound
  from the Motivation, expressed as a size: for a member of several times
  `chunk_size`, the largest yielded chunk stays below `2 * chunk_size`. An
  implementation that accumulated the archive would emit it as one large chunk
  and fail this. The content **must be incompressible** (`os.urandom`); see the
  note below.

### `app/mmt/projects/tests/test_downloads.py` — fixture

- **`project_with_downloads`** — a project owned by a known user, with three
  files written into its `download_directory`: `alpha.txt`, `Beta.txt` and
  `Gamma.txt`, each with distinct content. The mixed case is deliberate: a
  case-sensitive sort would order them `Beta.txt, Gamma.txt, alpha.txt`, so the
  expected `alpha.txt, Beta.txt, Gamma.txt` only holds if
  [`get_dir_contents`](../app/mmt/projects/utils.py) order is preserved. Every
  test below except the empty-directory one takes this fixture, so the setup is
  written once.

### `app/mmt/projects/tests/test_downloads.py` — `download_all`

- **`test_download_all_returns_zip`** — a project with downloadable files returns
  `200` with `Content-Type: application/zip`.
- **`test_download_all_content_disposition_filename`** — the header is
  `attachment; filename="{filename_safe(project.title)}.zip"`; asserts the date
  suffix of `directory_name` is not part of it.
- **`test_download_all_archive_contains_every_file`** — the only view test that
  reads the body, so the only `async def` one, using `AsyncClient` as described
  above. The collected streamed bytes re-open as a zip whose `namelist()` equals
  `['alpha.txt', 'Beta.txt', 'Gamma.txt']`, i.e. every file in the download
  directory in `get_dir_contents` order (case-insensitive by name).
- **`test_download_all_empty_download_directory_returns_404`** — a project whose
  download directory has no files.
- **`test_download_all_missing_download_directory_returns_500`** — a project
  whose download directory has been removed returns `500`. Distinguishes the
  broken invariant from the empty directory above, which returns `404`.
- **`test_download_all_other_users_project_returns_404`** — bob requesting alice's
  project, mirroring the existing ownership tests.
- **`test_download_all_anonymous_redirects_to_login`** — an unauthenticated
  request.

### `app/mmt/projects/tests/test_downloads.py` — "Download all" button

- **`test_project_detail_shows_download_all_button`** — with at least one
  downloadable file, the page contains a link to `projects:download-all`.
- **`test_project_detail_hides_download_all_button_without_files`** — with no
  downloadable files, that link is absent.

Both button tests locate the element the way the template assertions in
`test_views.py` already do: `BeautifulSoup` plus a `data-testid` attribute. The
button carries `data-testid="download-all-button"`.

## Slices and tasks

One slice; three tasks, each one session, tests first. Run backend tests with
`uv run pytest` from `app/`.

- [ ] **1. `zip_stream` helper.** Add `pytest-asyncio~=1.4` to the `dev`
  dependency group in [`pyproject.toml`](../app/pyproject.toml) first, since the
  tests are `async def` and are silently not awaited without it. Then add
  `zip_stream` (an async generator) and `_Sink` to
  [`utils.py`](../app/mmt/projects/utils.py). Done when the `test_utils.py` tests
  listed under Tests pass.

- [ ] **2. `download_all` view + route.** Add the view to
  [`views.py`](../app/mmt/projects/views.py) and the route to
  [`urls.py`](../app/mmt/projects/urls.py) per the reference above. The view
  reads `get_dir_contents(project.download_directory)`, returns `404` when it is
  empty, returns `500` when it raises `FileNotFoundError`, otherwise returns a
  `StreamingHttpResponse(zip_stream(files), ...)` with the decided
  `Content-Type` and `Content-Disposition`. Done when the `download_all` tests
  listed under Tests pass.

- [ ] **3. "Download all" button.** In
  [`project_detail.html`](../app/mmt/projects/templates/projects/project_detail.html),
  inside the "Downloadable files" section, add a button/link to
  `{% url 'projects:download-all' project.pk %}` carrying
  `data-testid="download-all-button"`, rendered only when there are downloadable
  files (reuse the existing `downloads`/count guard already in that section). Add
  the button label to `locale/de/LC_MESSAGES/django.po` and run
  `python manage.py compilemessages`. Done when the "Download all" button tests
  listed under Tests pass and `compilemessages` succeeds.

## Assumptions

- The download directory is flat and small in file count (tens, not thousands);
  no pagination or manifest is needed.
- Clients tolerate a `Content-Disposition` attachment without `Content-Length`
  (all mainstream browsers do; the single-file `download_download` view already
  streams without one).
- The response is served over ASGI (uvicorn, `app/Dockerfile`; the existing
  single-file download already uses an async generator). This is why `zip_stream`
  is an async generator rather than a synchronous one — see the streaming zip
  mechanism section for the reason. It is a decided part of the design, not an
  open question for the implementing session.

## Appendix: how the zipfile streaming works

This appendix is background for an implementing session that does not already
know the `zipfile` streaming API. It is explanatory, not a source of new
decisions; the binding decisions are in the sections above.

### What a zip file looks like on disk

A zip archive is not a container that is random-accessed; written from start to
end it is:

```
[local header + compressed data for member 1]
[local header + compressed data for member 2]
...
[central directory: one metadata record per member]
[end-of-central-directory record]
```

The central directory at the very end is an index of everything before it.
Normally `zipfile` writes each member's header, then after compressing the body
it seeks backwards to patch the header with the final compressed size and CRC.
Seeking backwards is impossible in an HTTP response: bytes already sent cannot be
rewritten.

### Why the sink exists

`zipfile.ZipFile(fileobj, 'w', ...)` writes to any object that has `write()` and
`flush()`. It probes that object for `seek`/`tell`:

- If present, it uses normal mode and patches headers by seeking back.
- If absent, it uses streaming mode: instead of patching the header afterwards,
  it writes the size and CRC in a small "data descriptor" record placed after the
  compressed body. Nothing is ever rewritten.

The `_Sink` is a minimal write-only object. It has `write` and `flush` but not
`seek`/`tell`, precisely to select that second mode:

```python
class _Sink:
    def __init__(self):
        self._buf = bytearray()
    def write(self, data):      # zipfile calls this with finished archive bytes
        self._buf += data
        return len(data)        # file-object contract: return the number of bytes written
    def flush(self):
        pass                    # ZipFile.close() calls flush(); nothing to do
    def take(self):             # our own method: drain and hand off what accumulated
        chunk = bytes(self._buf)
        self._buf.clear()
        return chunk
```

`zipfile` treats the sink as a file. Each `write()` appends to a `bytearray`.
After each step the generator calls `take()` to remove whatever accumulated and
`yield`s it to the HTTP response. The sink is the adapter between "zipfile writes
to a file object" and "the view wants a stream of chunks."

### The zipfile API calls used

| Call | What it does |
|---|---|
| `zipfile.ZipFile(sink, 'w', zipfile.ZIP_DEFLATED)` | Start an archive, writing into `sink`, default compression DEFLATE. |
| `zipfile.ZipInfo.from_file(path, arcname=path.name)` | Build the member's metadata by stating the file: its name, its mtime and its size. The size is what lets the next call pick 32-bit or 64-bit headers. |
| `archive.open(zinfo, 'w')` | Open one member for writing; returns a writer. The local header is written into the sink here, with 64-bit size fields when the stated size needs them. |
| `dest.write(data)` | Feed raw file bytes into that member. Compresses incrementally and pushes archive bytes into the sink. |
| leaving the `with archive.open(...)` block | Finalize the member: flush the compressor, write the data descriptor (size and CRC). |
| leaving the `with zipfile.ZipFile(...)` block | Write the central directory and end record for the whole archive. |

### The chunking loop

```python
async def zip_stream(files, chunk_size=65536):
    sink = _Sink()
    with zipfile.ZipFile(sink, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            zinfo = zipfile.ZipInfo.from_file(path, arcname=path.name)
            zinfo.compress_type = zipfile.ZIP_DEFLATED          # not inherited from the ZipFile
            with archive.open(zinfo, 'w') as dest:
                async with aiofiles.open(path, 'rb') as src:
                    while data := await src.read(chunk_size):   # read one chunk from disk
                        dest.write(data)                        # compress it into the archive
                        if chunk := sink.take():                # drain whatever archive bytes appeared
                            yield chunk                         # stream them to the client
            if chunk := sink.take():                            # member close produced trailing bytes
                yield chunk
    if chunk := sink.take():                                    # archive close produced the central directory
        yield chunk
```

The number of bytes written into a member does not map one-to-one to the number
of bytes produced. DEFLATE buffers internally, so a `dest.write()` may produce no
archive bytes yet, and a later flush produces a burst. That is why every `take()`
is guarded with `if chunk :=`: sometimes the buffer is empty and there is nothing
to yield. Memory stays bounded to roughly one chunk plus the compressor's small
internal buffer; the whole archive is never held at once.

### A worked trace

Produced with a synchronous harness for readability (in-memory files, a tiny
`chunk_size` of 10 bytes); the behavior of the `zipfile` and sink layer is
independent of sync versus async, only the read call differs. Two files: `a.txt`
is 15 bytes, so it is read in two chunks; `b.txt` is 25 bytes, so it is read in
three chunks. The file contents are repeated single characters, which compress
to almost nothing, so most of each header-bearing chunk is header, not data.

```
a.txt read#1 (10B in) -> sink had 35B -> YIELD chunk 1: 35 bytes
a.txt read#2 (5B in)  -> sink had  0B -> no yield        (DEFLATE buffered it)
a.txt member closed   -> sink had 21B -> YIELD chunk 2: 21 bytes
b.txt read#1 (10B in) -> sink had 35B -> YIELD chunk 3: 35 bytes
b.txt read#2 (10B in) -> sink had  0B -> no yield
b.txt read#3 (5B in)  -> sink had  0B -> no yield
b.txt member closed   -> sink had 21B -> YIELD chunk 4: 21 bytes
archive closed        -> sink had 124B-> YIELD chunk 5: 124 bytes
total archive: 236 bytes, namelist ['a.txt','b.txt'], testzip None, both round-trip OK
```

Reading it:

- **chunk 1 (35B):** opening `a.txt` wrote its local header (about 30 bytes) plus
  a little early compressor output. The content compresses to almost nothing, so
  most of the 35 bytes are header. Both members are far below the ZIP64 limit, so
  their headers carry no ZIP64 extra field; a member above 2 GiB would add 20
  bytes here and 8 more in the data descriptor.
- **read#2, no yield:** the last 5 bytes went into the compressor's buffer;
  nothing was emitted yet.
- **chunk 2 (21B):** closing the member flushed the compressed body and wrote the
  data descriptor; that is the burst.
- **chunks 3 and 4:** the same pattern for `b.txt`. Three reads produced output
  only on the first read and on close; the two later reads buffered.
- **chunk 5 (124B):** closing the `ZipFile` wrote the central directory (two
  entries) and the end record. This always comes last, which is why the archive
  is valid even though nothing was ever seeked.

Re-opening the concatenated 236 bytes: `namelist()` is correct, `testzip()`
returns `None` (no corruption), both members decompress back to the original
bytes, and `compress_type` is `8`, which is `zipfile.ZIP_DEFLATED`.

### The async part, for a reader familiar with JavaScript

| Python | JavaScript equivalent |
|---|---|
| `async def zip_stream(...)` with `yield` | `async function* zipStream(...)` — an async generator |
| `await src.read(chunk_size)` | `await fileHandle.read(...)` — await a promise |
| consumer: `async for chunk in zip_stream(...)` | `for await (const chunk of zipStream(...))` |
| `aiofiles.open(...)` | `fs.promises.open(...)` — the blocking read runs off the main thread and the result is awaited |

There is a single event loop per worker process. `await src.read(...)` is a
suspension point: the function pauses there and the event loop runs other pending
work (other HTTP requests this worker is handling) until the disk read completes,
then resumes. Django consumes the async generator with `async for` and writes
each yielded chunk to the socket.

The one part with no direct JavaScript analog: `zipfile`'s compression
(`dest.write`) is synchronous CPU code with no `await` inside it, so while a
single chunk compresses, the event loop is occupied. A 64 KB chunk compresses in
about a millisecond, and the `await` on the next read returns control to the
event loop immediately afterwards, so this does not delay other requests
noticeably.
