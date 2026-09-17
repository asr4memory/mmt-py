# Resources: grouping uploaded files and describing them

This is an executable spec. It is the authoritative record of the decisions for
grouping the uploaded files of a project into resources and for entering
descriptive metadata about them. An implementing session works from this
document and resolves ambiguity by reading it.

## Motivation

An uploaded file is currently related to a project and to nothing else. Several
files often belong to one thing: a recording that was split over three cards, a
video and a separate audio track of the same session, a broadcast in two parts.
The project detail page lists all of them side by side in one flat table, and
nothing in the database says which of them belong together.

The second gap follows from the first. The application stores technical
properties of a file (size, duration, media type, checksums) but nothing about
what was recorded: no title beyond the filename, no date, no place, no language,
no rights statement. That description belongs to the thing that was recorded,
not to each part of it, so it needs the grouping to exist first.

## Non-goals

- **No oral history vocabulary.** The institutions using the application record
  interviews, radio broadcasts, lectures and other material, and many of them do
  not publish to Oral-History.Digital. The model, the labels and the core
  metadata fields stay neutral about the kind of material. Role-specific fields
  such as "interviewee" are covered by the per-project fields of slice 4, not by
  columns.
- **Nothing moves on disk.** Grouping is a database relation. Files keep their
  names and their place in the project upload directory, so `file_path`, the
  upload and download routes, the ZIP download and the paths handed to the ASR
  service are untouched by this feature.
- **No nesting and no sharing.** A resource has no parent resource, and it
  belongs to exactly one project. A file belongs to at most one resource.
- **No bulk assignment in v1.** Files are assigned one at a time from the file
  detail page. A multi-select on the resource page is a later change.
- **No continuous playback across the parts.** The start offsets of slice 3 are
  computed and displayed; the player keeps playing one file at a time.
- **No per-file descriptive metadata.** A file that deserves a description gets
  a resource of its own, which is the ordinary case for a single recording.
- **The resource language does not yet steer transcription in v1.** The
  transcribe form keeps offering `WHISPERX_LANGUAGES`, which is shorter than the
  list a resource may carry (`other` and `mixed` have no alignment model). Using
  the resource language as the default for `TranscriptionJob` and
  `ProcessingRequest` is a later change.
- **No API.** `mmt/api` holds no source files at present; resources are not
  exposed over HTTP as JSON by this feature.

## Feature reference

### The app

A new app `mmt/resources`, added to `INSTALLED_APPS` as `'mmt.resources'`,
laid out like the existing apps: `models.py`, `forms.py`, `views.py`, `urls.py`,
`admin.py`, `validators.py`, `templates/resources/`, `tests/`.

`mmt/uploaded_files/models.py` refers to the model as the string
`'resources.Resource'`, because `mmt.resources` imports `Project` and a direct
import would close an import cycle.

### The model

```python
class Resource(TimestampedModel):
    class Type(models.TextChoices):
        INTERVIEW = 'interview', _('Interview')
        BROADCAST = 'broadcast', _('Radio or television broadcast')
        LECTURE = 'lecture', _('Lecture or talk')
        EVENT = 'event', _('Event recording')
        OTHER = 'other', _('Other')
```

| Field | Definition |
| --- | --- |
| `project` | `ForeignKey(Project, on_delete=CASCADE, related_name='resources', related_query_name='resource')` |
| `title` | `CharField(max_length=255)`, required |
| `identifier` | `CharField(max_length=128, blank=True, null=True, default=None)`, the institution's own signature |
| `description` | `TextField(blank=True, default='')` |
| `resource_type` | `CharField(max_length=32, choices=Type.choices, blank=True, default='')` |
| `date` | `CharField(max_length=10, blank=True, default='', validators=[validate_partial_date])` |
| `place` | `CharField(max_length=255, blank=True, default='')` |
| `language` | `CharField(max_length=10, blank=True, default='', choices=LANGUAGE_CHOICES)` |
| `creator` | `CharField(max_length=255, blank=True, default='')`, the producing person or institution |
| `rights` | `CharField(max_length=255, blank=True, default='')` |
| `notes` | `TextField(blank=True, default='')` |
| `custom_metadata` | `JSONField(default=dict, blank=True)`, filled in slice 4 |

`Meta`: `ordering = ['title', 'id']`, the usual `verbose_name` pair, and

```python
constraints = [
    models.UniqueConstraint(
        fields=['project', 'identifier'], name='unique_resource_identifier'
    ),
]
```

`identifier` is nullable rather than an empty string by default, unlike the
other optional character fields of this project. MySQL treats `NULL` as distinct
in a unique index, so any number of resources without an identifier can coexist,
while a conditional `UniqueConstraint` would be ignored by MySQL and MariaDB
altogether. The form maps empty input to `None` with
`forms.CharField(empty_value=None)`.

### Changes to `UploadedFile`

| Field | Definition |
| --- | --- |
| `resource` | `ForeignKey('resources.Resource', on_delete=SET_NULL, null=True, blank=True, related_name='files', related_query_name='file')` |
| `position` | `PositiveIntegerField(default=0)`, the order of the parts within the resource |

Both are additive and need no data migration. `Meta.ordering` of `UploadedFile`
stays `['created_at', 'filename']`; the order of the parts is a property of the
resource, not of the file table.

Deleting a resource sets `resource` to `NULL` on its files and touches nothing
on disk. Deleting a project deletes its resources, as it already deletes its
files.

### Derived values on `Resource`

```python
@property
def files_in_order(self) -> models.QuerySet:
    """The files of this resource, ordered by position, then created_at, then id."""

@property
def total_size(self) -> int:
    """The summed size of the files, in bytes."""

@property
def total_duration(self) -> int:
    """The summed duration of the files, in seconds."""

def start_offsets(self) -> dict[int, int]:
    """Maps file id to the start of that file on the resource timeline.

    The offset of a file is the summed duration of the files before it in
    files_in_order. A file whose duration is unknown counts as zero, so the
    offsets after it are too small; the display marks the resource as
    incomplete in that case.
    """
```

`total_size` and `total_duration` aggregate in the database. The resource list
annotates both with a single query over the project rather than calling the
properties per row.

### The partial date

`mmt/resources/validators.py`:

```python
def validate_partial_date(value: str) -> None:
    """Accepts YYYY, YYYY-MM and YYYY-MM-DD and nothing else."""
```

Archive records frequently give only a year or a year and a month, which is why
this is a character field and not a `DateField`. The value has to match
`^\d{4}(-\d{2}(-\d{2})?)?$`; a month has to be between `01` and `12`, and a full
date has to be accepted by `date.fromisoformat`. The error message is
`Enter a date as YYYY, YYYY-MM or YYYY-MM-DD.`

### The language list

`ProcessingRequest.LANGUAGE_CHOICES` moves to `mmt/core/languages.py` as
`LANGUAGE_CHOICES`, without the leading `(None, _('No selection'))` entry, which
is a form concern. `ProcessingRequest` keeps its attribute as
`LANGUAGE_CHOICES = [(None, _('No selection'))] + LANGUAGE_CHOICES`, so its
field, its migrations and its form are unchanged. `Resource.language` uses the
shared list and expresses "not stated" through `blank=True`.

### Routes

Creation is nested under the project, as `projects:create-file` already is;
everything else addresses the resource directly, as `uploaded_files` does.

| method & path | name | purpose |
| --- | --- | --- |
| `GET, POST /projects/<int:pk>/resources/create/` | `projects:create-resource` | create a resource in the project |
| `GET /resources/<int:pk>/` | `resources:detail` | metadata and the parts, in order |
| `GET, POST /resources/<int:pk>/edit/` | `resources:edit` | the metadata form |
| `POST /resources/<int:pk>/delete/` | `resources:delete` | delete, then redirect to the project |
| `POST /uploaded-files/<int:pk>/assign/` | `uploaded_files:assign` | set or clear the resource of one file |
| `GET /projects/<int:pk>/resources/export.csv` | `projects:export-resources` | slice 5 |
| `GET, POST /projects/<int:pk>/resources/import/` | `projects:import-resources` | slice 5 |

The three project routes begin with the literal segment `resources`, which no
existing pattern in `projects/urls.py` uses, so no ordering constraint applies
there.

Every view is `@login_required` and scopes by owner:
`get_object_or_404(Resource, pk=pk, project__user=request.user)`. A request for
another user's resource returns `404`, never `403`. Deletion and assignment are
`@require_POST` and answer a successful request with a redirect and a message
through `django.contrib.messages`, as the processing request views do.

### Templates

- `resources/detail.html`: the metadata as a definition list, the parts in
  order with their position, duration and start offset, the summed size and
  duration, and the edit and delete buttons.
- `resources/resource_form.html`: create and edit render the same form.
- `resources/_resource_table.html`: title, identifier, type, date, number of
  files, summed duration. Rendered on the project detail page.
- `resources/_metadata.html`: the definition list, so the detail page and a
  later export share it.

`projects/project_detail.html` gains a resources section above the uploaded
files section. `projects/_file_table.html` gains a Resource column between
Filename and Type, linking to the resource or showing an em dash. The uploaded
file detail page gains the assignment form: a select of the resources of the
file's own project, an empty option meaning unassigned, and a `position` number.

### Per-project metadata fields (slice 4)

Institutions describe their material differently, so the columns above are the
part that holds for all of them and everything else is defined per project.

```python
class MetadataField(TimestampedModel):
    class FieldType(models.TextChoices):
        TEXT = 'text', _('Text')
        LONGTEXT = 'longtext', _('Long text')
        DATE = 'date', _('Date')
        CHOICE = 'choice', _('Choice')
```

| Field | Definition |
| --- | --- |
| `project` | `ForeignKey(Project, on_delete=CASCADE, related_name='metadata_fields')` |
| `key` | `CharField(max_length=64, validators=[validate_metadata_key])`, matching `^[a-z][a-z0-9_]*$` |
| `label` | `CharField(max_length=128)` |
| `field_type` | `CharField(max_length=16, choices=FieldType.choices)` |
| `choices` | `JSONField(default=list, blank=True)`, a list of strings, read for `CHOICE` only |
| `order` | `PositiveIntegerField(default=0)` |
| `required` | `BooleanField(default=False)` |

`Meta`: `ordering = ['order', 'key']`, unique on `('project', 'key')`.

`Resource.clean()` validates `custom_metadata` against the definitions of its
project: every key needs a definition, a required field needs a non-empty value,
a `DATE` value passes `validate_partial_date`, and a `CHOICE` value is one of
`choices`. `save()` does not call `clean()`, so the form and the CSV import call
`full_clean()`; the admin does so already.

The resource form builds one additional form field per definition, in `order`,
and writes them back into `custom_metadata` as a flat mapping of key to string.
A key whose definition is deleted keeps its stored value but is not rendered and
not validated, so deleting a definition by accident does not destroy data.

Definitions are managed on the project settings page, as an inline formset.

### CSV export and import (slice 5)

One row per resource, UTF-8 with a BOM (`utf-8-sig`) so that Excel opens it
correctly, comma-separated, with a header row. The columns are `identifier`,
`title`, `resource_type`, `date`, `place`, `language`, `creator`, `rights`,
`description`, `notes`, followed by one column per metadata field of the
project, named by its `key`. The export file is named
`<project directory name>-resources.csv`.

The import reads the same format and matches rows on `identifier`:

- A row whose identifier is empty is an error. Matching on the title would make
  a renamed resource a new one.
- An unknown identifier creates a resource, a known one updates it. Nothing is
  ever deleted by an import.
- An unknown column is an error, so a misspelled header does not silently drop a
  column.
- The file is applied inside one `transaction.atomic` block. If any row fails,
  nothing is written and the form renders the errors as a list of row number and
  message. A partially imported file is never left behind.
- Assignment of files is not part of the CSV. Rows describe resources only.

## Slices and tasks

- [ ] **1 The model.** The `mmt.resources` app, `Resource` with the core
  metadata columns, `validate_partial_date`, the shared `LANGUAGE_CHOICES`, the
  two new fields on `UploadedFile`, both migrations, and the admin registration
  for `Resource` with `files` as an inline. Done when tests assert that
  `validate_partial_date` accepts `1998`, `1998-03` and `1998-03-17` and rejects
  `1998-13`, `1998-02-30`, `17.03.1998` and `''` through the model's
  `full_clean`; that two resources of one project may both have no identifier
  but not the same identifier, while two projects may each use the same one;
  that `files_in_order` orders by position and falls back to `created_at`; that
  `total_duration` and `start_offsets` return the summed and the cumulative
  seconds and count an unknown duration as zero; and that deleting a resource
  leaves its files with `resource` as `None` and `has_file` unchanged.

- [ ] **2 Resources in the interface.** Create, edit and delete a resource, the
  resources section on the project detail page, and the resource detail page
  with its metadata. Done when a view test asserts that a POST to
  `projects:create-resource` creates a resource in that project and redirects to
  its detail page; that a GET of the detail, edit and delete routes for another
  user's resource returns `404`; that a POST to `resources:delete` removes the
  resource, keeps its files and redirects to the project; and that an invalid
  `date` re-renders the form with the error and writes nothing.

- [ ] **3 Assignment and the parts list.** The assignment form on the uploaded
  file detail page, the Resource column in the file table, and the ordered parts
  with their start offsets and the summed size and duration on the resource
  page. Done when a view test asserts that a POST to `uploaded_files:assign`
  sets the resource and the position; that an empty selection clears the
  resource; that a POST naming a resource of another project, or of another
  user, returns `404` and changes nothing; and that the resource page lists
  three parts in position order with the offsets `0`, `d1` and `d1 + d2`.

- [ ] **4 Per-project metadata fields.** `MetadataField`, its management on the
  project settings page, the dynamic fields in the resource form, and the
  validation in `Resource.clean()`. Done when tests assert that a value for an
  undefined key, a missing required value, an invalid `DATE` value and a
  `CHOICE` value outside `choices` each raise `ValidationError` from
  `full_clean`; that a valid mapping is stored and rendered in `order`; and that
  deleting a definition leaves the stored value in `custom_metadata` untouched
  and its resource valid.

- [ ] **5 CSV export and import.** Both routes, the shared column list and the
  row errors. Done when tests assert that the export of a project with two
  resources and one metadata field has the specified header and two rows; that
  importing that file back changes nothing; that a row with a new identifier
  creates a resource and a row with a known one updates it; that an unknown
  column, an empty identifier and an invalid date each report the row number and
  leave the database unchanged; and that a file whose last row fails writes none
  of the earlier rows.
