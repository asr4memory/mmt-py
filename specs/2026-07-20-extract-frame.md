# Spec: Extract a frame from a video as a downloadable image

Status: draft, not started. New feature (the branch has no equivalent; its
"Regenerate poster" control is the closest thing, and this feature replaces the
user-facing half of that — see
[`2026-07-20-poster-image.md`](2026-07-20-poster-image.md)). Several
micro-decisions below are marked **OPEN**; resolve them with the author before
implementing.

This document is an **executable spec** (spec-driven development): it is the
prompt an implementing session works from and the authoritative record of every
decision, not a background sketch. Resolve ambiguity by reading this doc, not by
inventing; if a genuinely new decision comes up, write it into the doc as part
of the task. Check off tasks (`[x]`, with date) as they land. Do not duplicate
CLAUDE.md conventions here (test-first, pytest style, CSS units, translations in
both locales).

## Motivation

While watching an uploaded video, a user sometimes wants to keep a specific
frame as a still image: a face for identification, a document held up to the
camera, a slate. Today there is no way to do this except a screenshot outside
the application.

This feature lets the user pick the current playback position and extract that
frame as an image **at the source's original resolution**, stored as a derived
file belonging to the uploaded file. The user can extract several frames, and
can download or delete each one.

This is deliberately **not** the poster. The poster
([`2026-07-20-poster-image.md`](2026-07-20-poster-image.md)) is an invisible,
automatic, downscaled optimization the user never manages. An extracted frame is
the opposite: user-initiated, original resolution, and user-owned. The two share
only the `extract_frame` primitive in `media.py` (the poster passes
`max_height=480`; this feature passes `max_height=None`).

## Non-goals (v1)

- **Not the poster.** This feature never writes `poster_path` and never sets
  `has_poster`. Setting an extracted frame as the video's poster is a possible
  later bridge and is explicitly out of v1.
- **No editing.** No crop, rotate, annotate or resize. One frame, extracted as
  is at original resolution.
- **No extraction from audio.** Video only.
- **No bulk or interval extraction.** One frame per user action at one position;
  no "every N seconds" or contact-sheet export.
- **No sharing between users or projects.** An extracted image belongs to its
  uploaded file and follows that file's ownership and permissions.

## Feature reference

### Model

A new model, one row per extracted frame (a video has many):

```python
class ExtractedImage(models.Model):
    uploaded_file = models.ForeignKey(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name='extracted_images',
        verbose_name=_('Uploaded file'),
    )
    position = models.FloatField(verbose_name=_('Position'))   # seconds
    width = models.PositiveIntegerField(default=0, verbose_name=_('Width'))
    height = models.PositiveIntegerField(default=0, verbose_name=_('Height'))
    status = models.CharField(
        max_length=16, default='pending', verbose_name=_('Status')
    )   # 'pending' | 'ready' | 'failed'
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))

    class Meta:
        ordering = ['created_at']
```

- **`status`.** Extraction runs in a background task (a large source can be slow
  to open), so the row exists before the file does. `pending` on creation,
  `ready` once the file is written and `width`/`height` are set, `failed` if the
  extraction returns `False`. The list UI shows the state and polls while any row
  is `pending`, reusing the polling pattern already in `detail.html`.
- **`width`/`height`.** Filled from the extracted image on success so the list
  can show the resolution without re-probing. `0` until ready.
- **Deletion cascades** with the uploaded file and the project.

**File path** (a property on the model):

```python
@property
def image_path(self) -> Path:
    return self.uploaded_file.file_path.parent / 'frames' / f'{self.pk}.{IMAGE_EXT}'
```

- A `frames/` subdirectory under the upload directory, **separate from `web/`**:
  `web/` is for invisible optimizations, `frames/` is for user-owned artifacts.
  Keeping them apart keeps the "what may I delete freely" boundary clear.
- Keyed by primary key, so two extractions at the same position never collide and
  the name needs no sanitizing.
- **OPEN — image format (`IMAGE_EXT`).** Recommendation: `png` (lossless,
  faithful, universally usable), accepting that a full-resolution PNG of a 4K
  frame is several megabytes — this is a user-requested export, so size is
  acceptable. Alternatives: `jpg` (much smaller, lossy) or `webp` (small,
  lossless or lossy, less universal as a downloaded file). The choice sets the
  served `Content-Type`, the download filename suffix, and whether
  `extract_frame` needs per-format quality handling beyond the WebP case the
  poster already exercises. **Decide before task 1.**

### Extraction primitive

Reuses [`extract_frame(src, dst, position, max_height=None)`](../app/mmt/uploaded_files/media.py)
from the poster spec, called with `max_height=None` (original resolution) and a
`dst` whose suffix is `IMAGE_EXT`. If `IMAGE_EXT` is a format whose ffmpeg
quality flag differs from WebP's `-q:v` (for example MJPEG's 1–31 scale), this
spec's task 1 extends the primitive's per-format encoding; if `IMAGE_EXT` is
`webp`, no change to the primitive is needed. This is the only coupling to the
poster feature.

### Background task

```python
@shared_task
def task_extract_frame(extracted_image_id: int) -> None:
    image = ExtractedImage.objects.select_related('uploaded_file').get(pk=extracted_image_id)
    src = image.uploaded_file.file_path
    if extract_frame(src, image.image_path, position=image.position):
        w, h = probe_image_dimensions(image.image_path)   # ffprobe
        ExtractedImage.objects.filter(pk=extracted_image_id).update(
            status='ready', width=w, height=h
        )
    else:
        ExtractedImage.objects.filter(pk=extracted_image_id).update(status='failed')
```

- The `is_video()` guard is enforced at the **view** (a frame is only ever
  created for a video), not repeated here.
- `probe_image_dimensions` is a small ffprobe helper in `media.py` returning
  `(width, height)`; reuse the existing ffprobe wrapper style.

### Endpoints

All under the uploaded-file namespace, ownership through
`get_object_or_404(..., project__user=request.user)`.

| method & path | name | behavior |
|---|---|---|
| `POST /uploaded-files/<pk>/frames/` | `uploaded_files:frame-create` | Read `position` via the existing position parsing (missing/invalid/negative → `400`; a video is required, else `400`). Create an `ExtractedImage(status='pending')`, enqueue `task_extract_frame`, redirect to the detail page with a success message. |
| `GET /uploaded-files/<pk>/frames/<image_pk>/download/` | `uploaded_files:frame-download` | `serve_file(..., as_attachment=True, filename=...)`; `404` when the row is not `ready` or the file is absent. |
| `POST /uploaded-files/<pk>/frames/<image_pk>/delete/` | `uploaded_files:frame-delete` | Unlink the file, delete the row, redirect to the detail page with a success message. |

- **Position parsing.** The rule the branch's `_parse_position` used (missing,
  non-numeric or negative → reject) is reused, but here an invalid position is a
  `400` rather than a fallback to a default, because there is no meaningful
  default frame for a user-chosen extraction. `0` is valid.
- **Permissions.** Create and delete require
  `uploaded_files.change_uploadedfile`; download requires
  `uploaded_files.view_uploadedfile`. A view-only user sees the list and can
  download but cannot create or delete.
- **OPEN — surfaces that offer the "Extract frame" control.** Recommendation:
  v1 puts the control and the list on the **uploaded-file detail page** only,
  where the `<video>` already exposes `currentTime` and the management UI has a
  home. The transcript editor is where users watch most, so offering the control
  there too is the obvious follow-up, but it needs the Vue player to post the
  position and is left out of v1 to keep the slice small. **Confirm.**

### Detail page

Inside the `is_video` block of a `complete` file, for a user with
`change_uploadedfile`:

- An "Extract frame" button in a POST form to `uploaded_files:frame-create` with
  a hidden `position` field, set from `video.currentTime` on submit (the same
  capture the branch used, now feeding a user artifact instead of the poster).
- A list of `uploaded_file.extracted_images`, newest or oldest first per the
  model ordering, each row showing a thumbnail (the image itself, CSS-constrained
  — no separate thumbnail is generated), its resolution and position, a download
  link and a delete form. A `pending` row shows a processing state; a `failed`
  row shows an error state and offers delete. The page polls the status endpoint
  while any row is `pending`.

**OPEN — thumbnail in the list.** Recommendation: display the full image scaled
down with CSS rather than generating a separate small file, so no second derived
artifact and no extra task. For a handful of frames per video the bytes are
acceptable. If lists grow large this can be revisited. **Confirm.**

### Admin

Register `ExtractedImage` read-only (list: uploaded file, position, resolution,
status, created). Extracted images are created through the app, never by hand
(`has_add_permission` returns `False`), mirroring `UploadedFileAdmin`.

## File layout

- **[`app/mmt/uploaded_files/media.py`](../app/mmt/uploaded_files/media.py)** —
  `probe_image_dimensions`; possibly a small per-format branch in `extract_frame`
  depending on `IMAGE_EXT` (see the primitive section).
- **[`app/mmt/uploaded_files/models.py`](../app/mmt/uploaded_files/models.py)** —
  the `ExtractedImage` model, its `image_path`, and `IMAGE_EXT`.
- **New migration** — creates `ExtractedImage`.
- **[`app/mmt/uploaded_files/tasks.py`](../app/mmt/uploaded_files/tasks.py)** —
  `task_extract_frame`.
- **[`app/mmt/uploaded_files/views.py`](../app/mmt/uploaded_files/views.py)** —
  `frame_create`, `frame_download`, `frame_delete`.
- **[`app/mmt/uploaded_files/urls.py`](../app/mmt/uploaded_files/urls.py)** — the
  three `frames` routes.
- **[`app/mmt/uploaded_files/admin.py`](../app/mmt/uploaded_files/admin.py)** —
  `ExtractedImageAdmin`.
- **[`app/mmt/uploaded_files/templates/uploaded_files/detail.html`](../app/mmt/uploaded_files/templates/uploaded_files/detail.html)**
  — the extract control, the list, and the capture script.
- **Tests:** `tests/test_media.py` (`probe_image_dimensions`), `tests/test_tasks.py`
  (`task_extract_frame`), and a new `tests/test_extract_frame.py` (the three
  endpoints and permissions). `extract_frame` itself is tested by the poster
  spec.

Key signatures the tests target:

```python
# media.py
IMAGE_EXT = 'png'   # OPEN, see above
def probe_image_dimensions(path: Path) -> tuple[int, int]

# models.py
class ExtractedImage(models.Model): ...
    @property
    def image_path(self) -> Path

# tasks.py
@shared_task
def task_extract_frame(extracted_image_id: int) -> None
```

## Tests

### `tests/test_media.py` — `probe_image_dimensions`

- **`test_probe_image_dimensions_returns_size`** — a known image returns its
  `(width, height)`.
- **`test_probe_image_dimensions_failure`** — a non-image input is handled per the
  other probe helpers (return sentinel or raise, matching `extract_duration`).

### `tests/test_tasks.py` — `task_extract_frame`

- **`test_task_extract_frame_ready_on_success`** — with `extract_frame` mocked to
  `True` and dimensions probed, the row becomes `ready` with `width`/`height` set.
- **`test_task_extract_frame_failed_on_failure`** — with `extract_frame` mocked to
  `False`, the row becomes `failed` and no file is expected.
- **`test_task_extract_frame_calls_primitive_at_position_original_size`** — the
  task calls `extract_frame(src, image_path, position=row.position)` with no
  `max_height` (original resolution).

### `tests/test_extract_frame.py` — endpoints

- **`test_frame_create_queues_task`** — a valid `position` creates a `pending`
  row and enqueues `task_extract_frame`, redirecting to the detail page.
- **`test_frame_create_rejects_invalid_position`** — missing / non-numeric /
  negative `position` is `400` and creates no row.
- **`test_frame_create_rejects_non_video`** — a non-video is `400`.
- **`test_frame_create_requires_change_permission`** — a view-only user is `403`.
- **`test_frame_download_serves_ready_image`** — a `ready` row downloads as an
  attachment with the right `Content-Type`.
- **`test_frame_download_404_when_not_ready`** — a `pending` or `failed` row is
  `404`.
- **`test_frame_delete_removes_row_and_file`** — delete unlinks the file and
  removes the row, redirecting to the detail page.
- **`test_frame_delete_requires_change_permission`** — a view-only user is `403`.
- **`test_frame_other_users_file_404`** — every endpoint `404`s for another user's
  file.

## Slices and tasks

Tests first. Backend tests with `uv run pytest` from `app/`, frontend with
`npx vitest run` from `app/`.

**Resolve the OPEN decisions (image format; which surfaces offer the control;
CSS thumbnail vs generated) before task 1.**

- [ ] **1. Model, migration, task, dimension probe.** Add `ExtractedImage`,
  `IMAGE_EXT`, `image_path`, the migration, `probe_image_dimensions` and
  `task_extract_frame`. If `IMAGE_EXT` is not `webp`, extend `extract_frame`'s
  per-format encoding. Done when the `test_media.py` and `test_tasks.py` tests
  above pass and `migrate` applies cleanly.

- [ ] **2. Endpoints.** Add `frame_create`, `frame_download`, `frame_delete` and
  the three routes, with the permission and ownership rules above. Add German
  translations for the message strings and run `compilemessages`. Done when the
  `test_extract_frame.py` tests pass.

- [ ] **3. Detail page.** Add the "Extract frame" control, the capture script,
  and the list with thumbnail, resolution, download and delete, plus the
  `pending`-row polling. Add German translations and run `compilemessages`. Done
  when the control creates a frame and the list renders `ready`, `pending` and
  `failed` states.

- [ ] **4. Admin.** Register `ExtractedImageAdmin` read-only. Presentational; no
  behavior test.

## Assumptions

- `ffmpeg` and `ffprobe` are on `PATH` in the worker image.
- Extraction runs in a Celery worker; the request cycle creates the row, serves
  a ready image, or deletes.
- The number of extracted frames per file is small (a handful), so the list is
  not paginated and full images are acceptable as CSS-scaled thumbnails.
