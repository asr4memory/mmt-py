# Spec: project cards on the project index

Status: slices 1 and 2 implemented, slice 3 not started. Extracted on
2026-10-12 from the code at commit `0eee5d4`; the decisions of slice 3 were
added on the same day.

This document is an **executable spec** (spec-driven development): it is the
prompt an implementing session works from and the authoritative record of every
decision, not a background sketch. Resolve ambiguity by reading this document,
not by inventing; if a genuinely new decision comes up, write it into this
document as part of the task. Check off tasks (`[x]`, with date) as they land.
Do not duplicate CLAUDE.md conventions here.

Unlike the other specs, this one was first written after the implementation, to
record the behaviour as it existed. The behaviour described below is the target
after slice 3. Where it differs from the code at `0eee5d4`, the difference is
named in the section "Changes in slice 3".

The architecture note is a section of this document, because the feature is one
view, two templates and one stylesheet.

## Motivation

A user with several projects needs to see them at once and open one of them.
The project index at `/projects/` shows one card per project of the user. A card
identifies the project by its title, shows how many files and transcripts it
holds and when it was last updated, and is a single link to the project's
detail page.

## Changes in slice 3

Compared with the code at `0eee5d4`:

1. **Layout.** The card had the title followed by a list of three lines:
   "Created at" with the date, the upload count and the download count. It now
   has two rows: the title, and below it the counts on the left and the date
   of the project's last update on the right, without a label. The creation
   date is no longer shown.
2. **File count.** The card counted every `UploadedFile` row as "uploads",
   including uploads that had not finished. It now counts complete files as
   "files", and appends the number of incomplete files as `(+n)` when there are
   any. A project without any file shows "No files yet".
3. **Transcript count.** New. The card shows the number of transcripts of the
   project's files, when there is at least one.
4. **Download count.** The card no longer shows the download count. The field
   `Project.downloadable_files_count` stays in the model and is marked for
   future removal.
5. **Order.** Since the upload count was annotated in 2.17.1, the query groups
   by project, and Django leaves out `Meta.ordering` in grouped queries
   (`django/db/models/sql/compiler.py`, `if self._meta_ordering: order_by =
   None`). The cards have therefore been in an unspecified order, in practice
   oldest first, since 2.17.1. Before, the order was newest created first. The
   view now sets the order with an explicit `order_by('-updated_at')`: the
   project updated most recently comes first, consistent with the date the
   card shows.
6. **Opening a project no longer counts as an update.** The project detail
   view saved the whole project row on every `GET`, to store
   `downloadable_files_count`, and so set `updated_at`. It now saves with
   `update_fields=['downloadable_files_count']`, which writes that column only
   and leaves `updated_at` unchanged.
7. **Styles.** The `.card` component changes its border colour to dark gray
   on hover and focus, on every page that uses it. The project card has a
   padding of `1rlh` on all four sides instead of `0.5rlh 1rlh`. The space
   between the title and the second row is `0.25rlh` instead of `0.5rlh`. The
   title of every card, on the project index and on the welcome page, is one
   line cut with an ellipsis, instead of at most two lines.
8. **Grid.** The project index uses the existing `.grid--default`, which has 1
   column below a container width of `40em` and 2 columns from `40em`, instead
   of `.grid--project` with up to 4 columns. `.grid--project` is removed.

## Non-goals

Do not add these, even where they would be easy:

- **No actions on the card.** The card has one link target. Rename, delete and
  settings are on the detail page and the settings page.
- **No description on the card.** `Project.description` is not shown.
- **No status on the card.** Processing requests, transcription jobs and the
  state of individual files are not summarised on the card, apart from the
  number of incomplete files.
- **No download count on the card.**
- **No derived date of the last activity in this spec.** The card shows
  `Project.updated_at`. A date that also reflects new or deleted files and
  transcripts replaces it in a later spec; see "The date of the last update".
- **No explanation of the incomplete count.** `(+n)` is plain text, without a
  tooltip, a label or a link to the incomplete files.
- **No removal of `downloadable_files_count` in this spec.** The field, its
  admin columns and the code that writes it stay; the removal is a later change.
- **No sorting, filtering, search or pagination.** The index shows every
  project of the user in one fixed order.
- **No projects of other users.** The index shows the authenticated user's
  projects only, superuser included. The admin is the place to see all projects.
- **No permission check beyond login.** The index requires a logged-in user and
  no model permission.
- **No client-side code.** The card is server-rendered HTML and CSS; there is no
  JavaScript and no Vue component for it.
- **No test for the number of queries.** The index uses one query (see the
  architecture note); this is not asserted by a test.

## Actors

- **User** — a logged-in account holder. The actor in UC-1 to UC-3.
- **Anonymous visitor** — a browser without a session. The actor in UC-4.

## System use cases

```mermaid
flowchart LR
  user([User])
  anon([Anonymous visitor])

  subgraph web["Web process"]
    uc1[UC-1 See the own projects]
    uc2[UC-2 See that no project exists]
    uc3[UC-3 Open a project from its card]
    uc4[UC-4 Be sent to the login page]
  end

  user --> uc1
  user --> uc2
  user --> uc3
  anon --> uc4
```

Each use case below is the authoritative description of one system behaviour.
The feature reference further down repeats the rules in a compact form; where
the two disagree, the feature reference is wrong and both are fixed together.

### UC-1 See the own projects

- **Actor:** User.
- **Precondition:** The user is logged in and owns at least one project.
- **Trigger:** `GET /projects/`, reached from the "Projects" navigation link,
  the breadcrumbs or the projects card on the welcome page.
- **Main flow:**
  1. The view selects the user's projects in one query, ordered by the time
     of the last update with the most recent first, with the number of complete files, the number
     of incomplete files and the number of transcripts annotated onto each row.
  2. The page renders the heading "Projects" and one card per project in that
     order.
  3. The first row of each card shows the title.
  4. The second row shows the summary on the left and the date of the
     project's last update, `Project.updated_at`, on the right. The date has no
     label.
  5. The summary is built from `c`, the number of complete files, `i`, the
     number of incomplete files, and `t`, the number of transcripts:
     - If `c + i` is 0, the summary is `No files yet`.
     - Otherwise it starts with `{c} file` or `{c} files`. If `i > 0`,
       ` (+{i})` follows.
     - If `t > 0`, ` · {t} transcript` or ` · {t} transcripts` follows.
       If `t` is 0, nothing follows and there is no separator.

     Examples: `No files yet`; `2 files`; `2 files (+1)`; `0 files (+1)`;
     `2 files · 1 transcript`; `2 files (+1) · 3 transcripts`.
  6. Below the cards, the link "Create a new project" leads to
     `/projects/create/`.
- **Postcondition:** No data is written.

### UC-2 See that no project exists

- **Actor:** User.
- **Precondition:** The user is logged in and owns no project.
- **Trigger:** `GET /projects/`.
- **Main flow:**
  1. The page renders the heading and the text "You have no projects yet." in
     place of the card grid.
  2. The link "Create a new project" is shown as in UC-1.

### UC-3 Open a project from its card

- **Actor:** User.
- **Precondition:** UC-1 has rendered the index.
- **Trigger:** The user activates a card by pointer or keyboard.
- **Main flow:** The browser follows the card's link to `/projects/<id>/`.
- **Alternative flow:** While the pointer is over a card, or the card's link
  has the focus, the card changes its background, gains a shadow and
  underlines its title. This is visual feedback only.

### UC-4 Be sent to the login page

- **Actor:** Anonymous visitor.
- **Trigger:** `GET /projects/` without a session.
- **Main flow:** The response is a redirect to
  `/accounts/login/?next=/projects/`.

## Entity relationship model

```mermaid
erDiagram
    USER ||--o{ PROJECT : "owns"
    PROJECT ||--o{ UPLOADED_FILE : "holds"
    UPLOADED_FILE ||--o{ TRANSCRIPT : "has"

    USER {
        int id PK
    }
    PROJECT {
        int id PK
        int user_id FK
        string title "max 128 characters, filename-safe"
        text description "not shown on the card"
        int downloadable_files_count "deprecated cache, not shown on the card"
        datetime created_at "auto_now_add"
        datetime updated_at "auto_now"
    }
    UPLOADED_FILE {
        int id PK
        int project_id FK
        string filename
        bool has_file "true: complete, false: incomplete"
    }
    TRANSCRIPT {
        int id PK
        int uploaded_file_id FK
    }
```

### Complete and incomplete files

A file is **complete** when `has_file` is true and **incomplete** when
`has_file` is false. In terms of `UploadedFile.status`:

| `status`     | Counted as |
|--------------|------------|
| `complete`   | complete   |
| `corrupt`    | complete   |
| `processing` | incomplete |
| `incomplete` | incomplete |
| `missing`    | incomplete |

A corrupt file is counted as complete, because the assembled file exists; the
checksum disagreement is shown on the detail page, not on the card.

### Transcripts

The transcript count is the number of `Transcript` rows whose uploaded file
belongs to the project, regardless of whether the file is complete. A file with
two transcripts contributes two.

### Derived values on the card

| Card value        | Source                                                         |
|-------------------|----------------------------------------------------------------|
| Title             | `Project.title`                                                |
| Date              | `Project.updated_at`                                           |
| Complete count    | `complete_files_count`, annotated, `has_file=True`             |
| Incomplete count  | `incomplete_files_count`, annotated, `has_file=False`          |
| Transcript count  | `transcripts_count`, annotated                                 |

### The date of the last update

The card shows `Project.updated_at` as an interim value. The field is
`auto_now` and is set by every `save()` of the project row, whichever field
changed, unless the save names `update_fields` without it. After slice 3 these
calls write it:

- changing the title or the description (`update_project_title`, the settings
  page);
- deleting a downloadable file. The view saves the whole project row together
  with the new `downloadable_files_count`. This is intended: deleting a file
  counts as an update of the project.

The project detail view also writes the project row on every `GET`, but with
`update_fields=['downloadable_files_count']`, so opening a project does not
change the date. At `0eee5d4` it saved the whole row, and the date on the card
would have been the date the user last opened the project.

Uploading a file, deleting an uploaded file, and creating, editing or deleting
a transcript do not write the project row and do not change the date. The later
spec described below covers them.

A later spec replaces `updated_at` on the card with a date that is derived
from the project and its content, including uploaded files, transcripts and
deletions. Until then, the card reads `updated_at` and nothing else; the
template does not compute a date from related rows.

### The deprecated download count

`Project.downloadable_files_count` caches the number of files in the project's
download directory. It is written by the project detail view and by the view
that deletes a downloadable file, and it is shown in the admin. After slice 3
nothing on the user-facing pages reads it. The field keeps its writers and its
admin columns, and a comment on the field states that it is no longer shown to
users and is to be removed. Its removal, including the migration, the writers
and the admin columns, is a later change and not part of this spec.

### Invariants

1. For every card, the complete count plus the incomplete count equals the
   number of `UploadedFile` rows of the project.
2. A project without files has no transcripts, so "No files yet" never hides a
   transcript count.
3. The index never shows a project whose `user_id` differs from the requesting
   user's identifier.
4. Rendering the index writes nothing to the database.

## Architecture note

### Request path

```mermaid
flowchart LR
  browser[Browser] -->|GET /projects/| nginx[nginx]
  nginx --> web["web container: project_index"]
  web -->|one SELECT with three COUNTs and GROUP BY| db[(MariaDB)]
  web -->|render project_index.html, include _project_card.html per project| browser
```

### Query cost

The view issues one query for the projects, with `LEFT OUTER JOIN` on the
uploaded files and on their transcripts, and `GROUP BY` on the project. The
number of queries does not grow with the number of projects. Before 2.17.1 the
count was taken once per card; the annotation replaced that.

The join on transcripts repeats each file row once per transcript of that file.
Every count is therefore `distinct=True`: the file counts count distinct file
identifiers and the transcript count counts distinct transcript identifiers.
Without `distinct`, a file with two transcripts would be counted twice.

### Ordering of grouped queries

Django leaves out `Meta.ordering` in a query that has a `GROUP BY`. Every
annotated aggregate adds one, so a query on `Project` with an aggregate has no
order unless it calls `order_by` itself. This is why the order is set in the
view and not left to the model.

### Template isolation

`project_index.html` includes `projects/_project_card.html` with
`project=project only`. The card template receives the project and nothing
else from the page context. A value the card needs must therefore be an
attribute or annotation of the project object, which keeps the data the card
depends on visible in the view's query.

### Shared card component

The visual card is the generic component in
[`card.css`](../app/assets/css/components/card.css), also used by the welcome
page with the modifier `card--special`. The project card uses `card--default`.
A change to the base `.card` rules changes both pages; the dark gray border on
hover and focus and the one-line title are such changes and apply to the
welcome cards too. `.card--project`, `.card__details` and `.card__date` are
used by the project card only.

## Feature reference

### Route

| Method | Path          | Name             | View            | Decorators                       |
|--------|---------------|------------------|-----------------|----------------------------------|
| GET    | `/projects/`  | `projects:index` | `project_index` | `require_GET`, `login_required`  |

Any other method receives `405`. An anonymous request receives a redirect to
the login page with `next` set (UC-4).

### Query

```python
(
    Project.objects.filter(user=request.user)
    .annotate(
        complete_files_count=Count(
            'uploaded_files',
            filter=Q(uploaded_files__has_file=True),
            distinct=True,
        ),
        incomplete_files_count=Count(
            'uploaded_files',
            filter=Q(uploaded_files__has_file=False),
            distinct=True,
        ),
        transcripts_count=Count('uploaded_files__transcript', distinct=True),
    )
    .order_by('-updated_at')
)
```

The annotation `uploaded_files_count` is replaced by the three annotations
above. `Transcript.uploaded_file` sets `related_query_name='transcript'`, so
the lookup is `uploaded_files__transcript`.

### Page markup

- Breadcrumb "Projects", heading `h1` "Projects".
- With projects: `div.grid-wrapper > ul.grid.grid--default`, one `li` per card.
- Without projects: `p.u-ll` "You have no projects yet.".
- Always: `a.button-link[data-testid="new-project-link"]` to `projects:create`.

### Card markup

```html
<li class="card card--default card--project">
  <a class="card__link" href="/projects/<id>/" data-testid="project-card">
    <h3 class="card__title">{title}</h3>
    <p class="card__details u-mt-tiny">
      <span data-testid="project-card-summary">{summary}</span>
      <time class="card__date" datetime="{updated_at|c}">{updated_at|SHORT_DATE_FORMAT}</time>
    </p>
  </a>
</li>
```

- The whole card is one anchor, so the entire card area is the click target and
  the anchor is the only focusable element.
- `data-testid="project-card"` is on the anchor, not on the `li`. Tests and the
  Selenium test select the anchor by it. `data-testid="project-card-summary"`
  is on the summary, so tests read the summary without the date.
- The title is auto-escaped by the template engine.
- The date uses `SHORT_DATE_FORMAT` of the active locale (Django's default:
  `m/d/Y` in English, `d.m.Y` in German); the `datetime` attribute uses ISO 8601.
- The counts are numerals, pluralised with `blocktranslate count`. The file
  phrase is pluralised over `c`; a `c` of 0 uses the plural form.
- The suffix ` (+{i})` and the separator ` · ` (a space, U+00B7 MIDDLE DOT, a
  space) are written in the template outside the translated strings. They are
  the same in every language and have no translation entry.
- There is no download count, no creation date and no label for the date on
  the card.

### Layout

The grid is sized by container queries on `.grid-wrapper`
(`container-type: inline-size`), not by viewport media queries:

| Container width | Columns |
|-----------------|---------|
| below 40em      | 1       |
| from 40em       | 2       |

These are the rules of the existing `.grid--default`, which no template used at
`0eee5d4`. `40em` is the boundary between the mobile and the desktop layout.
`.grid--project` and its container queries are removed from `grid.css`.

The gap between cards is `1rlh`.

### Card appearance

- Padding of the link: `1rlh` on all sides, set by
  `.card--project .card__link`. The base `.card__link` padding of
  `0.5rlh 1rlh` is unchanged, so the welcome cards keep it. The link inherits
  the text colour and has no underline.
- Title: bold, `1rem`, line height `1rlh`, one line. A title wider than the
  card is cut with an ellipsis. The base `.card__title` rule replaces the
  two-line clamp (`-webkit-box-orient`, `-webkit-line-clamp`,
  `display: -webkit-box`) with `display: block`, `overflow: hidden`,
  `text-overflow: ellipsis` and `white-space: nowrap`. This applies to the
  welcome cards too, whose titles are short. The full title is not repeated in
  a `title` attribute; it is in the document and is read by screen readers.
- Details row (`.card__details`): `display: flex`, `flex-wrap: wrap`,
  `column-gap: 1rlh`, `0.875rem`, line height `1rlh`, colour `--text-muted`,
  `margin-bottom: 0`. The list rules (`list-style-type`, `padding-left`) are
  removed, because the element is no longer a list. The space of `0.25rlh`
  above the row comes from the existing utility `u-mt-tiny` in the markup,
  which replaces `u-mt-small`; `.card__details` sets no `margin-top`.
- Date (`.card__date`): `margin-left: auto`, which places it at the right edge
  of the row. When the card is too narrow for the summary and the date on one
  line, the date wraps onto a second line and stays right-aligned.
- On `:hover` and `:focus-within`: background `--color-blue-92`, border colour
  `--color-gray-30` (`#4d4d4d`), a shadow, and an underlined title. The
  transition takes 125 ms and covers background colour, border colour and
  shadow. The border colour is set in the base `.card:hover, .card:focus-within`
  rule. The rules `.card--default:hover`, `.card--default:focus-within`,
  `.card--special:hover` and `.card--special:focus-within`, which set the
  border colour back to `--color-blue-81`, have the same specificity as the
  base rule and come after it, so they would override it; they are removed.

### Translations

| msgid                                  | German                                   | Source of msgid           |
|----------------------------------------|------------------------------------------|---------------------------|
| `Projects`                             | `Projekte`                               | shared                    |
| `%(counter)s file` / `files`           | `%(counter)s Datei` / `Dateien`          | card, new                 |
| `%(counter)s transcript` / `transcripts` | `%(counter)s Transkript` / `Transkripte` | card, new               |
| `No files yet`                         | `Noch keine Dateien`                     | card, new                 |
| `You have no projects yet.`            | `Sie haben noch keine Projekte.`         | index                     |
| `Create a new project`                 | `Neues Projekt erstellen`                | shared with welcome page  |

The entries `%(counter)s upload` / `uploads` and `%(counter)s download` /
`downloads` have no other user and are removed from `django.po` in slice 3.
`Created at` stays, because `TimestampedModel.created_at` uses it.

## File layout

```
app/mmt/projects/
    views.py                                  project_index; project_detail saves
                                              with update_fields
    models.py                                 Project; deprecation comment on
                                              downloadable_files_count
    urls.py                                   projects:index
    templates/projects/project_index.html     page, grid, empty state, create link
    templates/projects/_project_card.html     one card
    tests/test_project_card.py                summary and order
    tests/test_views.py                       index shows own projects, hides others, redirects
    tests/test_project_updated_at.py          which requests change updated_at
    tests/test_selenium.py                    opens a project through its card

app/assets/css/components/
    card.css                                  .card, .card--default, .card__*
    grid.css                                  .grid, .grid--default; .grid--project removed

locale/de/LC_MESSAGES/django.po
```

Key signature:

```python
# mmt/projects/views.py
@require_GET
@login_required
def project_index(request) -> HttpResponse: ...
```

## Tests

- `projects/tests/test_project_card.py` (pytest style), rewritten. Each case
  asserts the full text of the element `project-card-summary`, with whitespace
  collapsed:
  - a project without files: `No files yet`;
  - a project with two complete files and no transcript: `2 files`;
  - a project with two complete files and one incomplete file: `2 files (+1)`;
  - a project with one incomplete file only: `0 files (+1)`;
  - a project with two complete files and one transcript: `2 files · 1 transcript`;
  - a project with one complete file that has two transcripts and one more
    complete file: `2 files · 2 transcripts`. This case fails if the counts are
    not distinct;
  - a project with `downloadable_files_count` set to 3: the card contains no
    text containing `download`;
  - a project whose `created_at` and `updated_at` are set to different days
    with `QuerySet.update` (which does not apply `auto_now`): the `datetime`
    attribute of the card's `time` element is the ISO 8601 form of
    `updated_at`;
  - two projects of the user, P1 inserted before P2, with `created_at` and
    `updated_at` set with `QuerySet.update` so that P1 has the later
    `created_at` and P2 the later `updated_at`: the card of P2 comes first.
    The expected order differs from both the primary key order and the
    creation order, so the test fails against the code at `0eee5d4` and
    against an `order_by('-created_at')`.
- `projects/tests/test_project_updated_at.py` (pytest style), new:
  - `GET` on the project detail page writes the current
    `downloadable_files_count` and leaves `updated_at` unchanged. Before the
    request, `updated_at` is set to a past day with `QuerySet.update`, and the
    stored count differs from the number of files in the download directory.
    This test fails against the code at `0eee5d4`;
  - deleting a downloadable file sets `updated_at` to a time later than the
    past day set before the request.
- `projects/tests/test_views.py` (`TestCase` style), unchanged — the index of
  the owner contains a card with the project's title and the create link; the
  index of another user contains no card; an anonymous request is redirected to
  the login page.
- `projects/tests/test_selenium.py`, unchanged — the end-to-end test navigates
  to the index and opens the project through the card's anchor.

The layout, the date's position and format, and the absence of a label are
presentational and are not tested.

## Slices and tasks

Each slice leaves the system working and independently deployable.

- [x] **1 Card on the index.** The index renders one card per project with the
  title, the creation date and both counts, linking to the detail page.
  Landed with the introduction of projects, before this spec.
- [x] **2 Card revision.** The "Created at" label, the title underline on hover
  and focus, the upload count as a query annotation (2026-07-26, `3afb96a`), and
  the two-line clamp of the title (2026-07-26, `3f8addb`). The annotation also
  removed the newest-first order of the cards; slice 3 sets an explicit order.
  Done when `test_project_card.py` passes. Released in 2.17.1.
- [ ] **3 Two-row card with file and transcript counts.** The three
  annotations and the explicit `order_by('-updated_at')` in `project_index`;
  `update_fields` on the save in `project_detail`; the two-row
  markup with the summary and the right-aligned date of the last update in
  `_project_card.html`;
  the `.card__details`, `.card__date` and `.card--project .card__link` rules,
  the one-line `.card__title`, the dark gray hover border and the removal of
  the modifier hover rules in `card.css`; `.grid--default` in
  `project_index.html` and the removal of `.grid--project` from `grid.css`; the deprecation
  comment on `downloadable_files_count`; the new translation entries, the
  removal of the upload and download entries from `django.po`, and
  `compilemessages`; the CHANGELOG entry.
  Done when the rewritten `test_project_card.py` and the new
  `test_project_updated_at.py` pass and the index in a development run shows
  the most recently updated project first, keeps the order when a project is
  only opened, `No files yet` for an empty
  project, `n files (+m) · k transcripts` for a project with an unfinished file
  and transcripts, and the date at the right edge of the second row.
