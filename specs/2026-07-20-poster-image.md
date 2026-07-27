# Spec: Poster image for an uploaded video

Status: implemented on the `transcode-web-video` branch; this document is the
retroactive executable spec that redevelopment follows. The branch merged two
different things into one — an invisible playback optimization (the poster) and
a user action (capture the current frame) — and this spec separates them. The
poster keeps only the optimization half; the user-facing capture becomes its own
feature ([`2026-07-20-extract-frame.md`](2026-07-20-extract-frame.md)). This is
therefore not a straight description of the branch.

This document is an **executable spec** (spec-driven development): it is the
prompt an implementing session works from and the authoritative record of every
decision, not a background sketch. Resolve ambiguity by reading this doc, not by
inventing; if a genuinely new decision comes up, write it into the doc as part
of the task. Check off tasks (`[x]`, with date) as they land. Do not duplicate
CLAUDE.md conventions here (test-first, pytest style, CSS units, translations in
both locales).

## Motivation

A `<video>` element with no `poster` attribute shows a blank or black frame
until the user presses play. Two surfaces embed an uploaded video: the
uploaded-file detail page and the transcript editor's media player. A poster
image gives each a representative still frame before playback.

The poster is an **invisible optimization**, in the same family as the 480p web
video ([`2026-07-20-web-video.md`](2026-07-20-web-video.md)) and the later web
audio and web image versions: it is generated automatically, downscaled, stored
under `web/`, and **never managed by the user as a file**. The user sees the
poster only as the still the player shows before playback; there is no list of
posters, no download, no delete, no per-file regeneration.

This is the distinction the branch missed. A separate, user-facing feature lets
the user capture the current frame as an image they own, at original resolution,
which they can download and delete
([`2026-07-20-extract-frame.md`](2026-07-20-extract-frame.md)). That is not the
poster. The poster stays automatic and invisible.

## Assessment of the branch implementation

The branch works but conflated the poster (an optimization) with a user action
(regenerate the poster from the current playback position). This spec keeps the
optimization and removes every user-facing part of it.

**Removed from the branch (moved to the extract-frame feature or dropped):**

- The `regenerate_poster` view, the `regenerate-poster` route, `_parse_position`,
  and `tests/test_regenerate_poster.py`. The user-facing "capture this frame"
  need they served is met by the extract-frame feature, which produces a
  user-owned image rather than overwriting the optimization.
- The "Regenerate poster" form and the position-capturing script in
  `detail.html`.
- The `position` parameter on `task_generate_poster`. The poster is generated at
  one automatic position; there is no caller-supplied position anymore.

**Revised (this spec differs from the branch):**

1. **Downscaling is a parameter of the extraction, not baked in.** The branch's
   `extract_poster_image` always wrote the frame at the source's full
   resolution. This spec introduces a general `extract_frame(src, dst, position,
   max_height=None)` primitive; the poster calls it with `max_height=480` so the
   poster equals the web-video rendition size, while the extract-frame feature
   calls the same primitive with `max_height=None` for an original-size image.
   "We sometimes need a larger image, but not in this app" lives here: the size
   is the caller's choice.
2. **Unique temporary file per extraction.** The branch used a deterministic
   temp path (`dst.stem + '.tmp' + dst.suffix`). This spec gives the temp file a
   random component so two concurrent extractions for the same file cannot write
   and rename the same temp file. See the web-video spec for why that one keeps a
   deterministic name and this one does not (it is enqueued once; extraction is
   shared with a user-triggered feature).

**Open decision, deferred (you will decide later): default frame selection.**
v1 keeps the branch's fixed default position of 2 seconds (`DEFAULT_POSTER_POSITION
= 2.0`), clamped into range. The candidate replacement is ffmpeg's content-aware
`thumbnail` filter, which analyzes a batch of frames and picks the most
distinctive one, removing the reliance on a fixed timestamp that sometimes lands
on a black intro. Because there is no user regeneration anymore, a better
automatic default matters more; but the `thumbnail` choice (batch size, whether
to pre-skip with `-ss`, its cost profile) is not settled, so v1 ships the fixed
default and this decision stays open. When it is made, it changes only the
`position=None` branch of `extract_frame` and the poster's call; nothing else in
this spec depends on it.

**Kept from the branch:** WebP output at `-q:v 80` served as `image/webp`; atomic
write; `POSTER_TIMEOUT = 5 * 60`; the out-of-range position clamp via an ffprobe
duration lookup; enqueue before the web video; the `poster` view's `404`-when-
absent; the `has_poster` flag; the admin column; the `poster` attribute on both
players.

## Non-goals (v1)

- **No web video.** Separate feature and spec
  ([`2026-07-20-web-video.md`](2026-07-20-web-video.md)).
- **No user-facing frame capture.** The user's "extract this frame as an image I
  can download and delete" feature is a separate spec
  ([`2026-07-20-extract-frame.md`](2026-07-20-extract-frame.md)). The poster has
  no user controls at all.
- **No poster for audio.** Audio has no video frame; `task_generate_poster`
  returns early for a non-video.
- **No content-aware frame selection in v1.** See the open decision above.
- **No `has_poster` reset when the source is missing.** `task_generate_poster`
  sets it `True` on success; nothing sets it back. A later-missing source makes
  the `poster` view `404` and the `<video>` shows no poster. Acceptable.
- **No multiple sizes.** One WebP at the web-video frame size, used by both
  players.

## Feature reference

### Model field

Added to [`UploadedFile`](../app/mmt/uploaded_files/models.py):

```python
has_poster = models.BooleanField(
    default=False,
    verbose_name=_('Has poster'),
    help_text=_(
        'A poster image is generated automatically with a background job '
        'for videos.'
    ),
)
```

Set to `True` only by `task_generate_poster` after a successful extraction. The
0013 migration
([`0013_uploadedfile_has_poster_uploadedfile_has_web_video`](../app/mmt/uploaded_files/migrations/))
adds this field alongside `has_web_video`, which belongs to the web-video spec.

### Derived-file path

```python
@property
def poster_path(self) -> Path:
    return self.file_path.parent / 'web' / (self.filename + '.webp')
```

In the `web/` subdirectory beside the web video, appending `.webp` to the full
filename, inheriting the per-project uniqueness of `filename` exactly as
[`web_video_path`](../app/mmt/uploaded_files/models.py) does.

### Frame extraction primitive

[`extract_frame(src, dst, position, max_height=None) -> bool`](../app/mmt/uploaded_files/media.py)
in `media.py`. This is the shared primitive; the poster and the extract-frame
feature both call it. It extracts one still frame:

```python
cmd = [
    'ffmpeg',
    '-y',
    '-ss', str(position),
    '-i', str(src),
    '-frames:v', '1',
    # scale filter present only when max_height is not None:
    # '-vf', f"scale=-2:'min({max_height},floor(ih/2)*2)'",
    '-update', '1',
    '-q:v', '80',   # webp quality when dst is .webp
    str(tmp),
]
```

Decided conventions:

- **`position` (seconds), required.** Input seeking (`-ss` before `-i`), fast;
  snapping to the nearest preceding keyframe is acceptable for a still. The
  `position=None` → automatic-selection branch is reserved for the open
  frame-selection decision and is **not** built in v1; every v1 caller passes a
  concrete position.
- **`max_height`.** `None` writes the frame at the source's full resolution (no
  `-vf`). A value adds the web-video scale expression
  `scale=-2:'min(max_height,floor(ih/2)*2)'`: cap the height, never upscale, keep
  even dimensions. The poster passes `POSTER_MAX_HEIGHT = 480`.
- **Output format follows `dst`'s suffix.** The poster's `dst` is `.webp`, so the
  primitive encodes WebP at `-q:v 80` (libwebp's 0–100 scale, higher is better).
  The extract-frame feature will choose its own suffix and, if it needs a format
  whose quality flag differs, extends the primitive's per-format handling in its
  own spec; v1 exercises only `.webp`.
- **Position clamp.** Before running ffmpeg the primitive probes the source
  duration (`extract_duration(src)`) and, when the duration is known and
  `position` is not in `[0, duration)`, replaces it with `duration / 2`, then
  clamps to at least 0. ffmpeg does not clamp: seeking past the end yields an
  empty output and an error.
- **Atomic write with a unique temp file.** Write to a temporary sibling whose
  name has a random component, for example
  `dst.parent / f'{dst.stem}.{uuid4().hex}.tmp{dst.suffix}'`, and
  `tmp.replace(dst)` only on success. `mkdir(parents=True, exist_ok=True)` on the
  destination directory first. On `CalledProcessError` or `TimeoutExpired`,
  remove the temp file and return `False`; the unique name means a failing run
  removes only its own temp file.
- **Timeout `POSTER_TIMEOUT = 5 * 60`.**
- **Return value and logging.** `True` on success, `False` on
  `CalledProcessError` or `TimeoutExpired`, logging through
  `_log_failure('Frame extraction', src, exc)`.

### Background task

[`task_generate_poster(uploaded_file_id)`](../app/mmt/uploaded_files/tasks.py):

```python
@shared_task
def task_generate_poster(uploaded_file_id: int) -> None:
    uploaded_file = UploadedFile.objects.get(pk=uploaded_file_id)
    if not uploaded_file.is_video():
        return
    if extract_frame(
        uploaded_file.file_path,
        uploaded_file.poster_path,
        position=DEFAULT_POSTER_POSITION,
        max_height=POSTER_MAX_HEIGHT,
    ):
        UploadedFile.objects.filter(pk=uploaded_file_id).update(has_poster=True)
```

- No `position` parameter: the poster is generated at the automatic default only.
- Returns early for a non-video (`test_task_generate_poster_skips_non_video`).
- Sets `has_poster=True` only on success, with a filtered `.update()`
  (`test_task_generate_poster_leaves_flag_unset_when_extraction_fails`).

Enqueued from [`task_assemble_chunks`](../app/mmt/uploaded_files/tasks.py) after
assembly, inside the `if uploaded_file.is_video():` branch and **before**
`task_generate_web_video`
(`test_task_assemble_chunks_assembles_and_enqueues_followups`,
`test_task_assemble_chunks_does_not_enqueue_poster_for_audio`). The media type
is detected synchronously in `task_assemble_chunks` so that this condition can
be evaluated at the enqueue point; that mechanism and its rationale are
specified in the web-video spec
([`2026-07-20-web-video.md`](2026-07-20-web-video.md), "Enqueue and synchronous
media-type detection"), which owns it. If the poster feature is implemented
first, it creates the branch and the synchronous detection along with it. The
`is_video()` guard inside `task_generate_poster` stays regardless, because the
task is also re-runnable by hand.

### Serving endpoint

[`poster(request, pk)`](../app/mmt/uploaded_files/views.py), route
`GET /uploaded-files/<pk>/poster/`, name `uploaded_files:poster`:

- `@require_GET`, `@permission_required('uploaded_files.view_uploadedfile')`,
  ownership through `get_object_or_404(..., project__user=request.user)`.
- `404` (`HttpResponseNotFound('Poster does not exist.')`) when `poster_path` is
  not a file (`test_poster_returns_404_when_missing`,
  `test_poster_other_user_gets_404`).
- Otherwise `serve_file(request, poster_path, content_type='image/webp')`
  (`test_poster_serves_image_when_present`).

There is no regenerate endpoint.

### Detail page and transcript editor

- [`detail.html`](../app/mmt/uploaded_files/templates/uploaded_files/detail.html):
  the `<video>` carries `poster="{% url 'uploaded_files:poster' uploaded_file.id %}"`
  only when `uploaded_file.has_poster`. No regenerate form and no
  position-capturing script.
- Transcript editor: `has_poster` threads through
  [`edit.html`](../app/mmt/transcripts/templates/transcripts/edit.html) →
  [`transcript.ts`](../app/assets/js/transcript.ts) →
  [`transcript_table.vue`](../app/assets/js/transcript/transcript_table.vue) →
  [`media_bar.vue`](../app/assets/js/transcript/media_bar.vue) →
  [`media_player.vue`](../app/assets/js/transcript/media_player.vue), building
  `posterURL = hasPoster ? '/uploaded-files/<id>/poster/' : undefined` and setting
  the `<video>`'s `poster` attribute. Unchanged from the branch.

### Admin

[`UploadedFileAdmin`](../app/mmt/uploaded_files/admin.py) lists `has_poster` in
`readonly_fields`.

## File layout

- **[`app/mmt/uploaded_files/media.py`](../app/mmt/uploaded_files/media.py)** —
  `extract_frame`, `DEFAULT_POSTER_POSITION = 2.0`, `POSTER_MAX_HEIGHT = 480`,
  `POSTER_TIMEOUT`, and the shared `_log_failure`.
- **[`app/mmt/uploaded_files/models.py`](../app/mmt/uploaded_files/models.py)** —
  the `has_poster` field and `poster_path`.
- **[`app/mmt/uploaded_files/migrations/0013_uploadedfile_has_poster_uploadedfile_has_web_video.py`](../app/mmt/uploaded_files/migrations/)**
  — adds `has_poster` (and `has_web_video`, owned by the web-video spec).
- **[`app/mmt/uploaded_files/tasks.py`](../app/mmt/uploaded_files/tasks.py)** —
  `task_generate_poster` and its enqueue before the web video.
- **[`app/mmt/uploaded_files/views.py`](../app/mmt/uploaded_files/views.py)** —
  `poster`. The `regenerate_poster` view and `_parse_position` are **removed**.
- **[`app/mmt/uploaded_files/urls.py`](../app/mmt/uploaded_files/urls.py)** — the
  `poster` route. The `regenerate-poster` route is **removed**.
- **[`app/mmt/uploaded_files/admin.py`](../app/mmt/uploaded_files/admin.py)** —
  `has_poster` in `readonly_fields`.
- **[`app/mmt/uploaded_files/templates/uploaded_files/detail.html`](../app/mmt/uploaded_files/templates/uploaded_files/detail.html)**
  — the `poster` attribute only; the regenerate form and script are **removed**.
- **Frontend:** `edit.html`, `transcript.ts`, `transcript_table.vue`,
  `media_bar.vue`, `media_player.vue` (poster plumbing, unchanged).
- **Tests:** `tests/test_media.py`, `tests/test_tasks.py`, `tests/test_views.py`.
  `tests/test_regenerate_poster.py` is **removed**.

Key signatures the tests target:

```python
# media.py
DEFAULT_POSTER_POSITION = 2.0
POSTER_MAX_HEIGHT = 480
def extract_frame(src: Path, dst: Path, position: float, max_height: int | None = None) -> bool

# models.py
@property
def poster_path(self) -> Path

# tasks.py
@shared_task
def task_generate_poster(uploaded_file_id: int) -> None
```

## Tests

The extraction tests build a real clip with ffmpeg and probe the output.

### `tests/test_media.py` — `extract_frame`

- **`test_extract_frame_writes_a_frame`** — a 360p source at `position=1.0` with
  `max_height=480` yields a `webp` image at 640×360 (360 ≤ 480, so unchanged).
- **`test_extract_frame_downscales_to_max_height`** — a 720p source with
  `max_height=480` yields height 480.
- **`test_extract_frame_original_size_when_no_max_height`** — a 720p source with
  `max_height=None` yields height 720 (no scaling).
- **`test_extract_frame_clamps_position_past_end`** — a position past a short clip
  still produces a frame (the middle-of-clip clamp).
- **`test_extract_frame_creates_missing_destination_dir`** — the `web/` parent is
  created when absent.
- **`test_extract_frame_failure_returns_false_and_leaves_no_output`** — a
  non-video input returns `False` and writes no `dst`.
- **`test_extract_frame_timeout_returns_false_and_leaves_no_output`** — a mocked
  `TimeoutExpired` returns `False` and leaves the directory empty (the unique
  temp file is removed).

### `tests/test_tasks.py` — `task_generate_poster` and enqueue

- **`test_task_generate_poster_extracts_and_sets_flag`** — with `extract_frame`
  mocked to `True`, the task calls it with
  `(file_path, poster_path, position=DEFAULT_POSTER_POSITION, max_height=POSTER_MAX_HEIGHT)`
  and sets `has_poster=True`.
- **`test_task_generate_poster_leaves_flag_unset_when_extraction_fails`** — with
  the extraction mocked to `False`, `has_poster` stays `False`.
- **`test_task_generate_poster_skips_non_video`** — an audio upload never calls
  the extraction.
- **`test_task_assemble_chunks_assembles_and_enqueues_followups`** — for a video
  upload, `task_generate_poster.delay` is called once with the file pk.
- **`test_task_assemble_chunks_does_not_enqueue_poster_for_audio`** — for an
  audio upload, `task_generate_poster.delay` is not called.

### `tests/test_views.py` — poster serving

- **`test_poster_serves_image_when_present`** — `200`, `image/webp`, poster bytes.
- **`test_poster_returns_404_when_missing`** — `404` with no poster file.
- **`test_poster_other_user_gets_404`** — another user's file is `404`.

## Slices and tasks

Tests first. Backend tests with `uv run pytest` from `app/`, frontend with
`npx vitest run` from `app/`.

- [ ] **1. Frame extraction primitive.** Add `extract_frame`,
  `DEFAULT_POSTER_POSITION`, `POSTER_MAX_HEIGHT` and `POSTER_TIMEOUT` to
  [`media.py`](../app/mmt/uploaded_files/media.py), with the optional scale
  (revision 1) and unique temp file (revision 2). Done when the `test_media.py`
  `extract_frame` tests pass.

- [ ] **2. Model field, path, task and enqueue.** Add the `has_poster` field and
  migration, the `poster_path` property, `task_generate_poster` (no position
  parameter), and its enqueue before the web video. Add the German translation
  for the field and run `compilemessages`. Done when the `test_tasks.py` poster
  tests and the assemble-enqueue test pass and `migrate` applies cleanly.

- [ ] **3. Serving endpoint and remove the regenerate machinery.** Add the
  `poster` view and route. **Remove** `regenerate_poster`, `_parse_position`, the
  `regenerate-poster` route, `tests/test_regenerate_poster.py`, and the
  regenerate form and script in `detail.html`; add the conditional `poster`
  attribute. Done when the `test_views.py` poster tests pass and no
  regenerate-poster references remain.

- [ ] **4. Transcript editor poster.** Thread `has_poster` through the frontend
  so the editor's `<video>` carries the poster when present. Done when the media
  player renders the `poster` attribute for a file with a poster (frontend test
  alongside the component). Unchanged from the branch; verify only.

- [ ] **5. Admin.** Add `has_poster` to `readonly_fields`. Presentational; no
  behavior test.

## Assumptions

- `ffmpeg` and `ffprobe` are on `PATH` in the worker image.
- The extraction runs in a Celery worker; the request cycle only reads
  `has_poster` and serves the stored file.
- `is_video()` is reliable both at the enqueue point and inside
  `task_generate_poster`, because `task_assemble_chunks` detects the media type
  synchronously before enqueuing anything.
