# Spec: transcript export in several formats

Status: in progress; slices 1a, 1b and 2 landed.

This document is an **executable spec** (spec-driven development): it is the
prompt an implementing session works from and the authoritative record of every
decision, not a background sketch. Resolve ambiguity by reading this document,
not by inventing; if a genuinely new decision comes up, write it into this
document as part of the task. Check off tasks (`[x]`, with date) as they land.
Do not duplicate CLAUDE.md conventions here (test-first, pytest style).

The architectural overview that accompanies this spec is
[`docs/transcript-export-architecture.md`](../docs/transcript-export-architecture.md).
It records where the export layer sits and why; this spec records what is built.

## Motivation

A finished transcript is only useful outside the application. Subtitles go into
a video editor or a player, a table of segments goes into a spreadsheet or a
statistics tool, a TEI file goes into a corpus, a PDF goes to a person who reads
it. Today the transcript detail page offers exactly one download: the stored
mmt-transcript JSON, which no tool outside this project understands.

This feature adds an export section to the transcript detail page with one link
per format. The first set of formats is whisperX JSON with word timestamps,
WebVTT and SubRip for subtitles, CSV for segments, TEI XML, and PDF.

The stored content is unchanged by an export. Every format is a projection of
`Transcript.content`, computed on request, never persisted and never written
back.

## Non-goals

Do not add these, even where they would be easy:

- **No import.** No format listed here can be uploaded to create or update a
  transcript. The existing paths (ASR ingest, manual whisperX JSON upload) are
  untouched. In particular the whisperX export is not a round trip: exporting
  and re-importing loses the mmt identifiers.
- **No change to the stored content.** An export reads `Transcript.content` and
  writes nothing. Export results are not cached, not stored in the project's
  download directory and not attached to the transcript.
- **No background jobs.** Every export is produced inside the request. No Celery
  task, no polling, no progress display. See the size assumption below.
- **No export of several transcripts at once.** One transcript, one format, one
  file. No project-level "export everything" and no ZIP.
- **No rendering options.** The two options this feature carries, described
  under "Export options" below, both transform the content before any exporter
  runs. No option changes how a format writes what it was given: no choice of
  subtitle line length, no time offset, no font or page size for the PDF. Those
  are the next request and each is its own decision about defaults and
  interface.
- **No subtitle line wrapping or cue splitting.** One segment becomes one cue,
  however long it is, and its text is emitted on one line. Splitting a long
  segment into readable cues needs a rule about line length, reading speed and
  cue duration; that is its own feature.
- **No media redaction.** Applying a redaction to the text is part of this
  feature; silencing the corresponding range of the media file is not. That is
  the other half of the applying rule in
  [`2026-07-26-redactions.md`](2026-07-26-redactions.md) and belongs to whatever
  produces derived media.
- **No per-redaction replacement text.** Every redacted word becomes the marker
  `XXX`. There is no pseudonym and no per-redaction substitution, per that
  spec's own non-goal.
- **No unredacted export.** Applying the redactions is not an option. Every
  export route writes the marker, always. The stored, unredacted content stays
  available through `transcripts:detail-json`, which this feature does not
  change.
- **No mention or entity output.** The `mentions` map is not represented in any
  format in this first set. TEI has a natural place for it (`<persName>`,
  `<placeName>`), which is recorded as an open question, not built.
- **No change to `transcripts:detail-json`.** The view, the route and the
  response it produces are untouched. What changes is where the link to it sits
  on the detail page and what it is called; see "The stored content row" below.
- **No word-level timestamps in VTT, SRT, CSV or TEI.** Only the whisperX export
  carries word timings. This is the explicit request and it also keeps the four
  segment formats readable.

## Actors

- **User** — an authenticated account holder who owns the project the
  transcript belongs to and holds the `transcripts.view_transcript` permission.
  The only actor in this feature.

## System use cases

The overview shows the use cases and the one included case that all exports
perform.

```mermaid
flowchart LR
  user([User])

  subgraph page["Transcript detail page"]
    uc1[UC-1 See the available export formats]
  end

  subgraph export["Export"]
    uc2[UC-2 Export as whisperX JSON]
    uc3[UC-3 Export subtitles as WebVTT]
    uc4[UC-4 Export subtitles as SubRip]
    uc5[UC-5 Export segments as CSV]
    uc6[UC-6 Export as TEI XML]
    uc7[UC-7 Export as PDF]
    uc8[UC-8 Prepare the content for export]
  end

  user --> uc1
  user --> uc2
  user --> uc3
  user --> uc4
  user --> uc5
  user --> uc6
  user --> uc7

  uc2 -. include .-> uc8
  uc3 -. include .-> uc8
  uc4 -. include .-> uc8
  uc5 -. include .-> uc8
  uc6 -. include .-> uc8
  uc7 -. include .-> uc8
```

Each use case below is the authoritative description of one system behaviour.
The format reference further down repeats the details in a compact form; where
the two disagree, the format reference is wrong and both are fixed together.

### UC-1 See the available export formats and choose options

- **Actor:** User.
- **Precondition:** The user is logged in, owns the project and has the
  `transcripts.view_transcript` permission, which is what the transcript detail
  page already requires.
- **Trigger:** The user opens the transcript detail page.
- **Main flow:**
  1. The page shows an "Export" section below the existing download and edit
     actions.
  2. The section lists the stored content first, then one row per format in the
     order pinned below, each showing the row's name, a one-line description of
     what it contains and a download link.
  3. A format row's link points at the export route for that format, with no
     query string, which is the complete export. The stored content row's link
     points at `transcripts:detail-json`.
- **Alternative flow A — the user changes an option a row offers:** The
  corresponding query parameter is added to that row's request. The other
  formats' rows are unaffected; each row carries its own options. No row offers
  an option until slice 6, which decides what such a row looks like.
- **Alternative flow B — the user lacks `transcripts.view_transcript`:** The
  user does not reach the page at all; the existing view answers with the
  permission denial it already produces.
- **Postcondition:** None. Opening the page changes nothing.

### UC-2 Export as whisperX JSON

- **Actor:** User.
- **Precondition:** UC-1, and the user selected the whisperX format.
- **Trigger:** `GET /transcripts/<pk>/export/whisperx/`.
- **Main flow:**
  1. The system prepares the content (UC-8).
  2. The system builds a JSON document in whisperX output shape: a `segments`
     list with start, end, text, speaker and words; a flat `word_segments` list
     of every word in order; and the language when it is known.
  3. The system responds `200` with content type `application/json` and
     `Content-Disposition: attachment`.
- **Alternative flows:** See UC-8 for content and access failures.
- **Postcondition:** None. This is the only format carrying word-level
  timestamps.

### UC-3 Export subtitles as WebVTT

- **Actor:** User.
- **Precondition:** UC-1, and the user selected the WebVTT format.
- **Trigger:** `GET /transcripts/<pk>/export/vtt/`.
- **Main flow:**
  1. The system prepares the content (UC-8).
  2. The system writes a `WEBVTT` header, then one cue per segment with the
     segment's start and end as `HH:MM:SS.mmm` and the segment's text on one
     line, preceded by a voice tag when the segment has a speaker.
  3. The system responds `200` with content type `text/vtt; charset=utf-8` and
     `Content-Disposition: attachment`.
- **Alternative flow A — a segment has no speaker:** The cue carries no voice
  tag; the text is emitted alone.
- **Postcondition:** None.

### UC-4 Export subtitles as SubRip

- **Actor:** User.
- **Precondition:** UC-1, and the user selected the SubRip format.
- **Trigger:** `GET /transcripts/<pk>/export/srt/`.
- **Main flow:**
  1. The system prepares the content (UC-8).
  2. The system writes one numbered block per segment, counting from 1, with the
     time range as `HH:MM:SS,mmm --> HH:MM:SS,mmm` and the segment's text on one
     line, prefixed with the speaker's name and a colon when the segment has a
     speaker.
  3. The system responds `200` with content type
     `application/x-subrip; charset=utf-8` and `Content-Disposition: attachment`.
- **Alternative flow A — a segment has no speaker:** No prefix is written.
- **Postcondition:** None.

### UC-5 Export segments as CSV

- **Actor:** User.
- **Precondition:** UC-1, and the user selected the CSV format.
- **Trigger:** `GET /transcripts/<pk>/export/csv/`.
- **Main flow:**
  1. The system prepares the content (UC-8).
  2. The system writes a header row and one row per segment with the segment's
     position, start, end, speaker and text.
  3. The system responds `200` with content type `text/csv; charset=utf-8` and
     `Content-Disposition: attachment`.
- **Alternative flow A — a segment has no speaker:** The speaker cell is empty.
- **Alternative flow B — a segment's text contains a comma, a quotation mark or
  a line break:** The value is quoted according to RFC 4180 by the standard
  library's `csv` writer. No text is altered to avoid quoting.
- **Postcondition:** None.

### UC-6 Export as TEI XML

- **Actor:** User.
- **Precondition:** UC-1, and the user selected the TEI format.
- **Trigger:** `GET /transcripts/<pk>/export/tei/`.
- **Main flow:**
  1. The system prepares the content (UC-8).
  2. The system builds a TEI document: a header naming the transcript, the
     export date, the source recording and the language; a participant list with
     one `<person>` per speaker; a timeline with one `<when>` per distinct
     segment boundary; and one `<u>` element per segment referring to its
     speaker and to its two timeline points.
  3. The system responds `200` with content type
     `application/tei+xml; charset=utf-8` and `Content-Disposition: attachment`.
- **Alternative flow A — the content has no language:** The `<langUsage>`
  element and the document's `xml:lang` attribute are omitted.
- **Alternative flow B — a segment has no speaker:** Its `<u>` element carries
  no `who` attribute.
- **Postcondition:** None.

### UC-7 Export as PDF

- **Actor:** User.
- **Precondition:** UC-1, and the user selected the PDF format.
- **Trigger:** `GET /transcripts/<pk>/export/pdf/`.
- **Main flow:**
  1. The system prepares the content (UC-8).
  2. The system groups consecutive segments with the same speaker into speaker
     turns.
  3. The system renders a document with a title block naming the transcript, the
     project, the uploaded file, the creation date and the language, followed by
     one block per speaker turn showing the turn's start time, the speaker's
     name and the turn's text, and a page number in the footer.
  4. The system responds `200` with content type `application/pdf` and
     `Content-Disposition: attachment`.
- **Alternative flow A — a turn has no speaker:** The block shows the time and
  the text without a name.
- **Postcondition:** None.

### UC-8 Prepare the content for export

- **Actor:** User. Included by UC-2 to UC-7, never triggered on its own.
- **Precondition:** The user is logged in and has the
  `transcripts.view_transcript` permission.
- **Trigger:** Any export request.
- **Main flow:**
  1. The system loads the transcript owned by the requesting user, by the
     identifier in the route.
  2. The system reads the export options from the query string, taking the
     default for every parameter that is absent.
  3. The system parses the stored content into a `Transcript` model with
     `validate_mmt_content`. Every path that writes `Transcript.content` stores
     the model's own dump, so the stored content is an mmt-transcript document
     at all times and the export does not migrate it. The result is not saved.
  4. If the request asked to omit speaker names, the system clears the speakers
     from that model, producing a new validated `Transcript` model.
  5. The system hands the resulting model to the exporter its caller named and
     returns the exporter's bytes in a download response. The exporter replaces
     every redacted word with the marker as it writes.
- **Alternative flow A — the transcript does not exist, or belongs to a project
  of another user:** `404`. This is the existing behaviour of the transcript
  detail view and uses the same queryset filter.
- **Alternative flow B — the URL names a format that does not exist:** `404`
  from the URL resolver. There is one route per format, so such a request
  matches no route and this use case is never reached.
- **Alternative flow C — the option is passed to a format whose row does not
  offer it:** It is applied anyway. The option transforms the content rather
  than the format's output, so every format produces correct output either way.
  Which rows offer the control is a decision about the interface, not about what
  the route accepts.
- **Alternative flow D — the stored content does not parse:** There is no such
  flow. Content that is not a valid mmt-transcript document is a defect in
  whatever wrote it, so the parse error propagates and the request fails with a
  server error. The export neither repairs the content nor reports it as an
  outcome the user could act on.
- **Alternative flow E — the user lacks `transcripts.view_transcript`:** The
  existing `permission_required` behaviour applies, which redirects to the login
  page.
- **Postcondition:** None. Clearing the speakers is not persisted and no
  exporter writes back: the redacted words stay in `Transcript.content`.

## Entity relationship model

Two diagrams. The first is the persisted graph: exports read one `Transcript`
and, for the PDF and the TEI header, the objects above it. The second is the
structure inside the `content` column, which is a JSON document and not a set of
tables; it is the actual input of every exporter.

### Persisted entities

```mermaid
erDiagram
    USER ||--o{ PROJECT : "owns"
    PROJECT ||--o{ UPLOADED_FILE : "holds"
    UPLOADED_FILE ||--o{ TRANSCRIPT : "has"

    USER {
        int id PK
        string username
    }
    PROJECT {
        int id PK
        int user_id FK
        string title "PDF title block"
    }
    UPLOADED_FILE {
        int id PK
        int project_id FK
        string filename "PDF title block, TEI media url"
        string media_type "TEI media mimeType"
        int duration "TEI recording dur"
        datetime created_at
    }
    TRANSCRIPT {
        int id PK
        int uploaded_file_id FK
        string label "export filename, PDF and TEI title"
        json content "the export input"
        datetime created_at "PDF title block"
    }
```

Ownership is checked on the same path the detail view already uses:
`Transcript.objects.filter(pk=..., uploaded_file__project__user=user)`.

### Structure of `Transcript.content`

The mmt-transcript document, as defined in
[`app/mmt/transcripts/mmt_schema.py`](../app/mmt/transcripts/mmt_schema.py) and
described in [`docs/mmt-transcript-format.md`](../docs/mmt-transcript-format.md).
Relations here are containment and reference within one JSON document, not
foreign keys.

```mermaid
erDiagram
    TRANSCRIPT_DOC ||--o{ SPEAKER : "lists"
    TRANSCRIPT_DOC ||--o{ ENTITY : "maps"
    TRANSCRIPT_DOC ||--o{ MENTION : "maps"
    TRANSCRIPT_DOC ||--o{ REDACTION : "maps"
    TRANSCRIPT_DOC ||--|{ SEGMENT : "contains"
    SEGMENT ||--|{ WORD : "contains"
    SEGMENT }o--o| SPEAKER : "speakerId"
    WORD }o--o| SPEAKER : "speakerId"
    WORD }o--o| MENTION : "mentionId"
    WORD }o--o| REDACTION : "redactionId"
    MENTION }o--o| ENTITY : "entityId"

    TRANSCRIPT_DOC {
        string format "mmt-transcript"
        int version "1"
        string language "ISO 639-1, may be null"
    }
    SPEAKER {
        string id PK
        string name "may be empty"
        string color "not exported"
    }
    ENTITY {
        string id PK "not exported"
        string name "dropped when its last mention is redacted"
    }
    MENTION {
        string id PK "not exported"
        string label
        float score
        string entityId FK "not exported"
    }
    REDACTION {
        string id PK "not exported"
        string reason "not exported"
        float start "inert, not exported"
        float end "inert, not exported"
    }
    SEGMENT {
        string id PK "TEI xml:id only"
        float start "seconds"
        float end "seconds"
        string speakerId FK
    }
    WORD {
        string id PK "not exported"
        float start "seconds, whisperX only"
        float end "seconds, whisperX only"
        string word
        float score "whisperX only"
        string speakerId FK
        string mentionId FK "not exported"
        string redactionId FK "not exported; selects the XXX marker"
    }
```

No export option reads any part of this document. Every element is either
written by some format or dropped by all of them.

A segment has **no** text field. Its text is produced by joining its words with a
single space, and that is the only definition of a segment's text in every
format below.

### What each format carries

| Content element | whisperX | VTT | SRT | CSV | TEI | PDF |
| --- | --- | --- | --- | --- | --- | --- |
| Segment start and end | yes | yes | yes | yes | yes | turn start only |
| Word start and end | yes | no | no | no | no | no |
| Word confidence score | yes | no | no | no | no | no |
| Speaker name | yes | yes, voice tag | yes, text prefix | yes, column | yes, `<person>` and `who` | yes, per turn |
| Speaker colour | no | no | no | no | no | no |
| Segment and word ids | no | no | no | no | segment id as `xml:id` | no |
| Mentions and entities | no | no | no | no | no | no |
| Redaction marks | no | no | no | no | no | no |
| Redacted words as `XXX` | yes | yes | yes | yes | yes | yes |
| Language | yes | no | no | no | yes | yes |

The redaction rows say two different things. No format carries a redaction as a
mark, because a consumer of a subtitle file has nothing to do with the reason a
passage was withheld. Every format carries the effect: the redacted words read
`XXX` in all six, always.

Every format is lossy relative to the stored content. The stored
mmt-transcript document remains the authoritative record, which is why the
download of the stored content stays. It is also the only download that carries
the redacted words: it serves the stored content unchanged, as it does today.

## Feature reference

### Routes and views

Six routes in [`app/mmt/transcripts/urls.py`](../app/mmt/transcripts/urls.py),
one per format, each with its key written into the path:

```python
path('<int:pk>/export/whisperx/', views.export_whisperx, name='export-whisperx'),
path('<int:pk>/export/vtt/', views.export_vtt, name='export-vtt'),
path('<int:pk>/export/srt/', views.export_srt, name='export-srt'),
path('<int:pk>/export/csv/', views.export_csv, name='export-csv'),
path('<int:pk>/export/tei/', views.export_tei, name='export-tei'),
path('<int:pk>/export/pdf/', views.export_pdf, name='export-pdf'),
```

Each format has a distinct, linkable URL that can be bookmarked and shared, and
a URL naming a format that does not exist is a `404` from the URL resolver,
before any view runs.

Six views, one per route, each `@require_GET` and
`@permission_required('transcripts.view_transcript')` to match
`transcripts.detail`. Every one is a single call into a helper that holds
everything the six share:

```python
# mmt/transcripts/views.py
def _export(
    request: HttpRequest,
    pk: int,
    export: Callable[[mmt_schema.Transcript], bytes],
    extension: str,
    content_type: str,
) -> HttpResponse: ...

@require_GET
@permission_required('transcripts.view_transcript')
def export_vtt(request: HttpRequest, pk: int) -> HttpResponse:
    return _export(request, pk, export_to_vtt, 'vtt', 'text/vtt; charset=utf-8')
```

The exporter parameter is annotated `mmt_schema.Transcript`, written through the
module, because `views.py` already imports the Django model of the same name.

`_export` performs UC-8: it loads the transcript, reads the options, parses the
content, applies the transformation the options ask for and returns the download
response. `_export` is a helper and not a view; it is never routed to directly.

Each exporter is named for its format, `export_to_<key>`, and re-exported from
`exporters/__init__.py`, so `views.py` imports all six on one line:

```python
from mmt.transcripts.exporters import export_to_csv, export_to_pdf, ...
```

The names are distinct rather than six functions called `export`, so a function
passed as a value into `_export` still says which format it is, in the call site
and in a traceback.

There is no table mapping format keys to exporters. With one route per format,
nothing ever holds a format key as data: the key appears in the path, the view
name and the route name, and the exporter is named directly in the one view that
calls it. Reading a format's behaviour is following the route to the view to the
exporter module, with no lookup in between.

The three per-format values a response needs — the export function, the filename
extension and the content type — are arguments at that single call site rather
than entries in a structure. The cost is six near-identical view functions with
repeated decorators; the benefit is that no indirection exists to be understood,
and each format is one grep away from everything about it.

The format names, descriptions and the order they are listed in are not in the
Python code at all. They are written in the template, where the rest of this
application's user-visible text is written, and the order is whisperX, VTT, SRT,
CSV, TEI, PDF: the machine-readable full-fidelity format first, then the four
segment formats, then the format meant for reading.

Every exporter returns `bytes`, not `str`, so that the encoding decision belongs
to the exporter and the view never guesses one. The PDF exporter would otherwise
be the odd one out.

| Format | Route name | View | Exporter | Extension | Content type |
| --- | --- | --- | --- | --- | --- |
| whisperX | `export-whisperx` | `export_whisperx` | `export_to_whisperx` | `json` | `application/json` |
| WebVTT | `export-vtt` | `export_vtt` | `export_to_vtt` | `vtt` | `text/vtt; charset=utf-8` |
| SubRip | `export-srt` | `export_srt` | `export_to_srt` | `srt` | `application/x-subrip; charset=utf-8` |
| CSV | `export-csv` | `export_csv` | `export_to_csv` | `csv` | `text/csv; charset=utf-8` |
| TEI | `export-tei` | `export_tei` | `export_to_tei` | `xml` | `application/tei+xml; charset=utf-8` |
| PDF | `export-pdf` | `export_pdf` | `export_to_pdf` | `pdf` | `application/pdf` |

That table is documentation of what the six call sites say. It is not read by
anything.

### The exporter input

An exporter takes the validated `mmt_schema.Transcript` and nothing else:

```python
def export_to_whisperx(transcript: Transcript) -> bytes: ...
```

Not the raw content dict and not the Django model. Typed attribute access is the
point: an exporter that reads `segment.start` cannot silently produce `None` for
a key that a raw dict would happily return.

The view produces that model with `validate_mmt_content(transcript.content)`.
The call is a parse, not a guard: an exporter reads attributes, and building the
nested model tree from the stored dict is what pydantic's validation does. It is
not `normalize_content`, because the export reads content the backend itself
wrote and has nothing to upgrade; see "The stored content is already valid"
below. Its result is not saved (UC-8 postcondition).

#### The stored content is already valid

Every path that writes `Transcript.content` validates first and stores the
resulting model's dump: the manual upload form, the ASR ingest task, the
editor's `update_json`, and the `normalize_transcripts` command that upgraded
the rows predating them. Content in the legacy whisper shape therefore does not
reach an export, and an export that normalised on read would carry an upgrade
path for content nothing produces any more.

A document that does not parse is a defect in a writer, not a state the export
handles. The error propagates, the request fails with a server error, and the
row is visible as a bug instead of being repaired on the way out or reported as
a polite message. This is why no export view catches `ValidationError`.

Four formats need more than the transcript: TEI needs the uploaded file's name,
media type and duration for its header, and the PDF needs the label, the project
title, the file name and the creation date for its title block. Those exporters
take the values they need as keyword arguments, decided when each is written. A
structure bundling them is not defined in advance; two formats wanting the same
four values is not enough to justify one, and inventing it before either exists
means every exporter carries fields it never reads.

An exporter takes no options. The one option in this feature is applied to the
transcript before the exporter is called, and the redaction rule is not an
option at all.

### Redactions

Every export applies the transcript's redactions. This is not an option and
there is no way to obtain the original words through an export route.

Each exporter replaces a word carrying a `redactionId` with the marker `XXX`
where it reads the word's text, per the rule in
[`2026-07-26-redactions.md`](2026-07-26-redactions.md). One marker per word,
never one for the whole run, so every word keeps its own `id`, `start`, `end`
and `speakerId` and no segment loses words:

```python
# in each exporter module
REDACTION_MARKER = 'XXX'

def _word_text(word: Word) -> str:
    if word.redactionId is not None:
        return REDACTION_MARKER

    return word.word
```

Nothing rewrites the transcript. There is no redacted copy of the document
anywhere: a transformation producing one would return a `Transcript` claiming to
be a valid mmt-transcript when its words are no longer the transcript's words,
and it would have to clear `mentionId` and `redactionId` and then garbage-collect
the maps those references keep alive, all to satisfy the schema on a value that
is thrown away. Reading the marker at the point the word's text is needed avoids
inventing that document.

The mmt speaker, mention, entity and redaction maps are therefore untouched and
unread. No format carries any of them, so a redacted word leaks nothing through
them.

`REDACTION_MARKER` and `word_text` live in `exporters/words.py`, which every
exporter reads the word's text through. They started in the whisperX exporter
and moved there when the subtitle formats became the second and third callers.

### Export options

One option, read from the query string of the export route and applied to the
validated model before any exporter is called:

| Parameter | Absent means | `0` means |
| --- | --- | --- |
| `speakers` | speaker names are included | every speaker reference is cleared |

```python
@dataclass(frozen=True)
class ExportOptions:
    include_speakers: bool = True

    @classmethod
    def from_query(cls, query) -> 'ExportOptions': ...
```

Only the exact string `0` turns the option off. Any other value, including an
absent parameter, leaves the default. An unrecognised parameter is ignored
rather than rejected, so a stale bookmark keeps working.

The default is the complete export: a bare `/transcripts/1/export/vtt/` produces
output with speakers. The parameter appears in a URL only when someone asked for
the deviation, which is also what makes the checkbox on the detail page work
without a paired hidden field, since an unchecked box submits nothing.

#### The option is a content transformation

`clear_speakers` sets `speakerId` to `None` on every segment and every word and
empties the `speakers` list, and hands the result to an exporter that cannot tell
the option was used. Every format already specifies what it writes for a segment
without a speaker, as an alternative flow of its use case, so the option needs no
new behaviour from any exporter.

This is why there is no per-format option handling anywhere in the Python code,
and why the option is valid for every format: the exporters see nothing but a
transcript that is a legal mmt-transcript document.

```python
# mmt/transcripts/exporters/speakers.py
def clear_speakers(transcript: Transcript) -> Transcript: ...
```

### Filenames

`f'{filename_safe(label)}.{extension}'`, using `filename_safe` from
[`app/mmt/core/utils.py`](../app/mmt/core/utils.py). `filename_safe` raises
`ValueError` when the label reduces to an empty string, for example a label made
only of punctuation; the fallback name is then `transcript_{pk}`.

Every export is served with `Content-Disposition: attachment`, including the
PDF. A user who wants to read the PDF in the browser opens the downloaded file;
serving it inline would make the browser's viewer the default reading
experience for a document that is meant to be kept.

### Timecodes

One helper module, since the two subtitle formats need the same arithmetic
with different punctuation:

```python
# mmt/transcripts/exporters/timecode.py
def hhmmssmmm(seconds: float, *, millisecond_separator: str = '.') -> str:
    """Format seconds as HH:MM:SS.mmm. Hours are not truncated at 24 and are
    always at least two digits."""
```

VTT passes `'.'`, SRT passes `','`. Milliseconds are truncated, not rounded, so
that a cue never ends after the next one starts because of rounding.

No other format calls it. CSV writes seconds as a number, TEI writes the
origin's `absolute` and every other point as an interval in seconds, and the PDF
writes a turn's start as `HH:MM:SS` without milliseconds. Whether the PDF widens
this signature or formats its own time is decided in slice 5.

### Format: whisperX JSON — key `whisperx`

Content type `application/json`, extension `json`. Serialised with
`json.dumps(..., ensure_ascii=False, indent=2)` and encoded as UTF-8, so the
file is readable in an editor and umlauts are not escaped.

```json
{
  "language": "de",
  "segments": [
    {
      "start": 0.0,
      "end": 4.2,
      "text": "Hi, wie geht es dir?",
      "speaker": "Alice",
      "words": [
        {"word": "Hi,", "start": 0.0, "end": 0.3, "score": 1.0, "speaker": "Alice"}
      ]
    }
  ],
  "word_segments": [
    {"word": "Hi,", "start": 0.0, "end": 0.3, "score": 1.0, "speaker": "Alice"}
  ]
}
```

- `language` is omitted when the content's language is `null`, rather than
  written as `null`, because consumers of whisperX output expect a string there.
- `speaker` is the speaker's `name`, falling back to the speaker's `id` when the
  name is an empty string. The key is omitted when `speakerId` is `null`. The
  mmt speaker id is not exported, because whisperX's `speaker` field is a label,
  not a reference.
- `text` is the segment's words joined with a single space. whisperX word tokens
  carry their trailing punctuation (`"Hi,"`), so a plain space join reproduces
  the original spacing. No punctuation-aware joining is attempted.
- `word_segments` is every word of every segment, in document order, in the same
  shape as inside a segment. whisperX emits this list and downstream tools read
  it, so it is reproduced rather than left out.
- The mmt `id` fields of segments and words are not exported. They have no place
  in the whisperX shape, and a consumer that needs them uses the stored
  mmt-transcript JSON.

### Format: WebVTT — key `vtt`

Content type `text/vtt; charset=utf-8`, extension `vtt`. Lines end with `\n`.

```
WEBVTT

00:00:00.000 --> 00:00:04.200
<v Alice>Hi, wie geht es dir?

00:00:04.200 --> 00:00:07.900
Und dir?
```

- The file starts with `WEBVTT` and one blank line, and ends with a newline
  after the last cue's text. SubRip ends the same way.
- Cues are not numbered. VTT allows an optional identifier line; omitting it
  keeps the file smaller and no player requires it.
- The voice tag is `<v Name>` with the speaker's name, resolved like the
  whisperX `speaker` field. It is omitted for a segment without a speaker.
- The speaker's name is escaped for the four characters that are markup in VTT
  cue text: `&` becomes `&amp;`, `<` becomes `&lt;`, `>` becomes `&gt;`. The
  same escaping applies to the cue text itself.

### Format: SubRip — key `srt`

Content type `application/x-subrip; charset=utf-8`, extension `srt`. Lines end
with `\n`.

```
1
00:00:00,000 --> 00:00:04,200
Alice: Hi, wie geht es dir?

2
00:00:04,200 --> 00:00:07,900
Und dir?
```

- Blocks are numbered from 1 in document order.
- SubRip has no speaker convention, so the speaker's name is written as a text
  prefix `Name: `, resolved like the whisperX `speaker` field, so a speaker with
  an empty name is written as its id rather than as an empty prefix. It is
  omitted for a segment without a speaker.
- No escaping. SubRip text is plain text; the few players that understand HTML
  tags in it are not a reason to alter the transcript's characters.

### Format: CSV — key `csv`

Content type `text/csv; charset=utf-8`, extension `csv`. Written with the
standard library's `csv.writer` with default dialect, which is RFC 4180 with
`\r\n` line endings. Encoded as UTF-8 **with a byte order mark** (`utf-8-sig`),
because Excel otherwise reads a UTF-8 CSV as the system's legacy encoding and
shows broken umlauts, and a spreadsheet is the main reason this format exists.

Header row and one row per segment:

| Column | Value |
| --- | --- |
| `index` | position of the segment in the document, counting from 1 |
| `start` | segment start in seconds, three decimal places |
| `end` | segment end in seconds, three decimal places |
| `speaker` | the speaker's name, empty when the segment has no speaker |
| `text` | the segment's words joined with a single space |

Times are seconds and not `HH:MM:SS.mmm`: a spreadsheet can compute a readable
timecode from a number, while parsing a timecode string back into a number needs
a formula that most users will not write.

### Format: TEI XML — key `tei`

Content type `application/tei+xml; charset=utf-8`, extension `xml`. Built with
`xml.etree.ElementTree` and serialised with `encoding='utf-8',
xml_declaration=True`, so escaping is the standard library's responsibility and
not a set of format strings.

```xml
<?xml version='1.0' encoding='utf-8'?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="de">
  <teiHeader>
    <fileDesc>
      <titleStmt><title>Interview mit Alice</title></titleStmt>
      <publicationStmt>
        <p>Exported from the Media Management Tool on 2026-07-30.</p>
      </publicationStmt>
      <sourceDesc>
        <recordingStmt>
          <recording type="audio" dur="PT3600S">
            <media url="interview.wav" mimeType="audio/wav"/>
          </recording>
        </recordingStmt>
      </sourceDesc>
    </fileDesc>
    <profileDesc>
      <langUsage><language ident="de"/></langUsage>
      <particDesc>
        <listPerson>
          <person xml:id="s1"><persName>Alice</persName></person>
        </listPerson>
      </particDesc>
    </profileDesc>
  </teiHeader>
  <text>
    <body>
      <timeline unit="s" origin="#t0">
        <when xml:id="t0" absolute="00:00:00"/>
        <when xml:id="t1" interval="4.2" since="#t0"/>
      </timeline>
      <u xml:id="seg_a1" who="#s1" start="#t0" end="#t1">Hi, wie geht es dir?</u>
    </body>
  </text>
</TEI>
```

- `<recording type="...">` is `audio` when the uploaded file's media type is an
  audio type and `video` otherwise, decided with `file_category` from
  `mmt/core/utils.py`. `dur` is `PT{duration}S` with the uploaded file's
  duration, and the whole `<recordingStmt>` is omitted when the duration is 0,
  since `dur="PT0S"` would assert something false.
- Speaker ids become `xml:id` values on `<person>` and are referenced from `<u
  who="#...">`. The mmt speaker ids (`s1`, `s2`) are already valid XML names, so
  they are used unchanged. A speaker with an empty name gets a `<persName>`
  holding its id.
- `<particDesc>` is omitted entirely when the content has no speakers, rather
  than written as an empty `<listPerson>`. The TEI row offers no speaker option,
  but `?speakers=0` on the route reaches this exporter, and a transcript can
  legitimately have no speakers of its own.
- The timeline holds one `<when>` per **distinct** timestamp across all segment
  boundaries, so a segment that starts exactly where the previous one ends
  produces one point, not two. The first point is the origin `t0` with
  `absolute="00:00:00"`; every other point is `interval` seconds `since="#t0"`.
  Points are emitted in ascending order and named `t0`, `t1`, `t2` in that
  order.
- One `<u>` per segment, carrying the segment's mmt id as `xml:id`. This is the
  only format that exports mmt identifiers, because TEI needs an identifier
  anyway and reusing the stored one lets a TEI file be traced back to the
  transcript.
- `xml:lang` on `<TEI>` and the `<langUsage>` block are omitted when the
  content's language is `null`.
- No `<w>` elements. Word-level markup is what a word-timestamped TEI would
  need, and this format deliberately stops at the segment.

### Format: PDF — key `pdf`

Content type `application/pdf`, extension `pdf`. Rendered with WeasyPrint from a
Django template, the same approach as
[`app/mmt/my_account/pdf.py`](../app/mmt/my_account/pdf.py):

```python
# mmt/transcripts/exporters/pdf.py
def export_to_pdf(transcript: Transcript, *, label, project_title, filename, created_at) -> bytes:
    from weasyprint import HTML
    html = HTML(string=render_to_string('transcripts/export_pdf.html', {...}))
    return html.write_pdf()
```

The import of WeasyPrint stays inside the function, as it does in
`my_account/pdf.py`, so importing `views.py` does not pull in the rendering
stack.

The document:

- A4, 2 cm margins, `@page` footer with the page number, header with the
  transcript's label from page two onwards.
- A title block: the transcript's label as the heading, then the project title,
  the uploaded file's name, the transcript's creation date and the language.
- The body is one block per **speaker turn**, not per segment: consecutive
  segments with the same `speakerId` are joined into one paragraph, with the
  turn's start time in `HH:MM:SS` and the speaker's name above it. Reading a
  transcript segment by segment breaks a sentence every few seconds, and the
  segment boundaries carry no meaning for a reader.
- Turn text is the turn's segments' texts joined with a single space.
- A turn without a speaker shows the time alone.

The template is `app/mmt/transcripts/templates/transcripts/export_pdf.html` with
its CSS inline in a `<style>` block, following `dpa_pdf.html`. Per CLAUDE.md the
CSS uses `rlh` units and alphabetically ordered properties.

The turn grouping helper lives in `mmt/transcripts/exporters/turns.py`:

```python
@dataclass(frozen=True)
class SpeakerTurn:
    start: float
    end: float
    speaker: Speaker | None
    text: str

def speaker_turns(transcript: Transcript) -> list[SpeakerTurn]: ...
```

`speaker_turn_batches` in
[`app/mmt/transcripts/normalize.py`](../app/mmt/transcripts/normalize.py) groups
by the same rule but returns flat word dicts for the NER request and works on raw
dicts, so it cannot be reused here. If a third caller needs turns, the two are
merged then, not now.

### Detail page section

The export section is added to
[`app/mmt/transcripts/templates/transcripts/detail.html`](../app/mmt/transcripts/templates/transcripts/detail.html)
below the enrichment section and above the delete action, which is where the
page's read-only actions sit: the edit action and enrichment change the stored
content, an export only reads it. It is seven written-out rows: the stored
content first, then one per format in the order pinned above. The `detail` view is not changed
and puts nothing about export into its context.

Each format row is a link to the route of one format:

```html
<div class="action-row">
    <h3 class="action-row__name">{% translate "WebVTT subtitles" %}</h3>
    <p class="action-row__description">{% translate "Cues for a video player." %}</p>
    <a class="button-link action-row__action" href="{% url 'transcripts:export-vtt' transcript.id %}">{% translate "Download" %}</a>
</div>
```

The section is then a list of download links: a name, a description and a button
per row, in a main column that holds three controls today.

#### The stored content row

The link to `transcripts:detail-json`, which the page carries today as "Download
JSON" above every other action, becomes the first row of the section. A user
looking for a way to get the transcript out of the application finds every
answer in one place instead of one answer above the list of the others.

```html
<div class="action-row">
    <h3 class="action-row__name">{% translate "mmt-transcript JSON (stored content)" %}</h3>
    <p class="action-row__description">{% translate "The document as this application stores it, with every word as it was transcribed. The only download that is not redacted." %}</p>
    <a class="button-link action-row__action" download="{{ transcript.label }}.json" href="{% url 'transcripts:detail-json' transcript.id %}">{% translate "Download" %}</a>
</div>
```

The name and the description carry what the position no longer says. Standing
above the section, the link was visibly not one of the export formats; inside
it, only the words distinguish a download that applies the redactions from the
one that does not, and a row that read "Download JSON" would make the redaction
guarantee depend on which row a user picks without saying so.

The row keeps the `download` attribute, because `detail_json` returns a
`JsonResponse` with no `Content-Disposition` header and the browser would
otherwise display the JSON rather than save it. Every export route sets the
header itself, so no format row needs the attribute.

How a row carries the speaker option is decided in slice 6, together with the
option itself. A control that sends a query parameter needs the row to submit a
request rather than follow a fixed URL, which is a change to the rows that offer
it and to nothing else. It is not designed here, because a disclosure holding no
control and a form with no fields are both a link written the long way.

#### Which row offers which option

| | whisperX | VTT | SRT | CSV | TEI | PDF |
| --- | --- | --- | --- | --- | --- | --- |
| Omit speaker names | yes | yes | yes | no | no | yes |

CSV keeps the speaker column unconditionally, because a column is trivial to
remove in a spreadsheet and a control that saves nothing is noise. TEI keeps
`<particDesc>` and the `who` attributes unconditionally, because the participant
list is a large part of what makes the file useful in a corpus. The CSV and TEI
rows therefore have no disclosure at all: a name, a description and a button.

This table is a decision about the interface only. The route honours the option
for all six formats (UC-8 alternative flow C), so
`/transcripts/1/export/tei/?speakers=0` produces a TEI document without a
participant list even though the TEI row offers no such control. Constraining the
route to exactly what the interface offers would mean declaring per-format option
sets in Python and returning an error for a URL that would otherwise produce
correct output; that is not done.

A row is the `action-row` component in
`app/assets/css/components/action_row.css`, alongside the existing component
files. It is named for what it is, a row carrying a name, a description and one
action, rather than for this feature, so a later page with the same shape uses
it instead of copying it. Per CLAUDE.md it uses `rlh` units and orders
properties alphabetically. The section itself needs no class of its own.

### Translations

Format names and descriptions, the section heading, the "Options" and
"Download" labels and the option label are translatable strings, all marked in
`detail.html` or in the option partial. No export view produces a user-facing
message of its own. Per CLAUDE.md, the German translations go into
`locale/de/LC_MESSAGES/django.po` in the same session that introduces them,
followed by `compilemessages`.

Suggested German names: "whisperX JSON", "WebVTT-Untertitel",
"SubRip-Untertitel", "CSV-Tabelle", "TEI-XML", "PDF-Dokument". Suggested German
option label: "Sprechernamen weglassen".

## File layout

```
app/mmt/transcripts/
    exporters/
        __init__.py         re-exports the six export_to_* functions
        options.py          ExportOptions
        speakers.py         clear_speakers, speaker_labels_by_id
        timecode.py         hhmmssmmm
        turns.py            SpeakerTurn, speaker_turns
        words.py            REDACTION_MARKER, word_text
        whisperx.py         export_to_whisperx
        vtt.py              export_to_vtt
        srt.py              export_to_srt
        csv_export.py       export_to_csv
        tei.py              export_to_tei
        pdf.py              export_to_pdf
    templates/transcripts/
        export_pdf.html
        _export_option_speakers.html
    tests/
        test_export_view.py
        test_export_whisperx.py
        test_export_vtt.py
        test_export_srt.py
        test_export_csv.py
        test_export_tei.py
        test_export_pdf.py
        test_export_timecode.py
        test_export_turns.py
        test_export_options.py
```

`__init__.py` imports the exporter modules, so importing anything from the
package imports all six. That is why the PDF exporter keeps its WeasyPrint
import inside the function.

`app/assets/css/components/action_row.css` holds the row component the
section is built from.

The module is `csv_export.py` and not `csv.py`, so that it cannot shadow the
standard library's `csv` module for anything importing it.

Key signatures:

```python
# mmt/transcripts/views.py
def _export(
    request: HttpRequest,
    pk: int,
    export: Callable[[mmt_schema.Transcript], bytes],
    extension: str,
    content_type: str,
) -> HttpResponse: ...

def _export_filename(transcript: Transcript, extension: str) -> str: ...

@require_GET
@permission_required('transcripts.view_transcript')
def export_whisperx(request: HttpRequest, pk: int) -> HttpResponse: ...

# mmt/transcripts/exporters/whisperx.py
def export_to_whisperx(transcript: Transcript) -> bytes: ...

# mmt/transcripts/exporters/speakers.py
def clear_speakers(transcript: Transcript) -> Transcript: ...
```

## Tests

Exporter tests are pure: they call an exporter with a fixture transcript and
assert on the returned bytes. Only `test_export_view.py` needs the database and
the client.

A shared fixture in `app/mmt/transcripts/tests/conftest.py` provides a small
two-speaker, three-segment transcript with a known set of timestamps, including
one segment without a speaker, one speaker with an empty name, one word with an
umlaut and one redaction spanning two consecutive words, so every exporter test
covers the fallbacks and the marker. It comes in two forms: `export_content`,
the stored dict, and `export_transcript`, the same document validated.

- `test_export_view.py` — each format answers `200` with its content type and an
  attachment disposition whose filename ends in the format's extension; another
  user's transcript answers `404`; a user without
  `transcripts.view_transcript` is redirected; and a label that reduces to an
  empty string produces `transcript_{pk}.{ext}`. For the option: `?speakers=0`
  produces output without any speaker name, and is honoured for every one of the
  six formats, including CSV and TEI, whose rows do not offer the control; an
  unrecognised parameter and a value other than `0` are ignored.

  Two behaviours this feature specifies are deliberately not asserted here. A
  format key without a route answering `404` is the URL resolver's behaviour and
  not this application's. The redaction marker is asserted in each format's own
  test, at the exporter boundary where the substitution happens.
- `test_export_whisperx.py` — segment text joining, `word_segments` order and
  length, the speaker name and its id fallback, the omitted `speaker` key, the
  omitted `language` key, the absence of mmt `id` fields, and the marker in both
  the segment text and the word entry.
- `test_export_vtt.py` — the `WEBVTT` header, the timecode format with a dot,
  the voice tag and its absence, escaping of `<`, `>` and `&` in cue text and in
  a speaker's name, and one blank line between cues.
- `test_export_srt.py` — numbering from 1, the timecode format with a comma, the
  speaker prefix and its absence, and the absence of escaping.
- `test_export_csv.py` — the header row, three decimal places on the times, the
  empty speaker cell, RFC 4180 quoting of a text containing a comma and a
  quotation mark, and the byte order mark at the start of the file.
- `test_export_tei.py` — the document parses; the timeline has one point per
  distinct timestamp, ordered, with `t0` as the origin; `<u>` elements carry the
  segment ids and resolve their `who`, `start` and `end` references; the header
  omits `<recordingStmt>` for a zero duration and omits the language block for a
  null language; a speaker name containing `&` and `<` is escaped by the
  serialiser.
- `test_export_pdf.py` — the result starts with `%PDF-`, is longer than a
  threshold, and the rendered HTML (asserted on the template render, not on the
  PDF bytes) contains the turn grouping, the speaker names and the title block.

- `test_export_timecode.py` — `hhmmssmmm` truncates rather than rounds, formats
  hours beyond 24, and pads correctly.
- `test_export_turns.py` — `speaker_turns` merges consecutive equal speakers,
  treats `None` as a value like any other, and returns one turn for a
  speakerless transcript.
- `test_export_options.py` — `ExportOptions.from_query` maps an absent parameter
  and a value other than `0` to the default, maps `0` to the deviation, and
  ignores an unknown parameter; `clear_speakers` empties the speakers list, sets
  `speakerId` to `None` on every segment and word, returns a model that
  validates, and leaves the words themselves unchanged.
Each format's own test asserts the marker; there is no separate test file for
redactions, because there is no separate function transforming the document.

There is no test of the mapping from a format to its exporter, extension and
content type, because there is no structure holding it. `test_export_view.py`
asserts it end to end by requesting every route and checking the response.

## Slices and tasks

Each slice leaves the system working and independently deployable. Each task is
one session. Slice 1 carries the whole mechanism and one format; slices 2 to 5
each add formats to an existing mechanism, so they are small and can land in any
order. Slice 6 adds the speaker option to whichever formats exist by then; it is
last because it is orthogonal to every format and because no format has to be
aware of it.

- [x] **1a whisperX exporter.** `exporters/`, `export_to_whisperx` and the
  shared fixture. Done when `test_export_whisperx.py` passes. No route, no view,
  no template. Landed 2026-08-29.
- [x] **1b The view and the detail page.** `_export`, the `export_whisperx`
  view, its route, the export section on the detail page, and the German
  translations. Done when `test_export_view.py` passes and a development run
  downloads a whisperX file from the detail page. The export section lists only
  whisperX at this point; each later slice adds its own row. Landed 2026-08-30.
- [x] **2 WebVTT and SubRip.** Both exporters, `timecode.py`, their views, their
  routes and their rows on the detail page, with the German translations. Done
  when `test_export_timecode.py`, `test_export_vtt.py` and
  `test_export_srt.py` pass and a downloaded VTT file plays as subtitles beside
  the media file in a player. Landed 2026-08-30.
- [ ] **3 CSV.** The exporter, its view, its route, its row and the German
  translation. Done when `test_export_csv.py` passes and a downloaded file opens
  in a spreadsheet with correct umlauts.
- [ ] **4 TEI XML.** The exporter, its view, its route, its row and the German
  translation. Done when `test_export_tei.py` passes and the exported file
  validates against the TEI P5 schema in an external validator.
- [ ] **5 PDF.** `turns.py`, the exporter, the template, its view, its route,
  its row and the German translation. Done when `test_export_pdf.py` and
  `test_export_turns.py` pass and a development run produces a readable
  multi-page PDF from a real interview transcript.
- [ ] **6 The speaker option.** `exporters/options.py`,
  `exporters/speakers.py`, the option parsing in `_export`, the template
  partial, the disclosures on the rows named in the matrix above, the TEI
  `<particDesc>` rule, `action_row.css` and the German translation. Done when
  `test_export_options.py` passes, the option assertions in
  `test_export_view.py` pass, and a development run downloads a PDF with the box
  ticked that shows the times and the text without any speaker name.

## Open questions

Recorded, not blocking. Do not decide these while implementing; raise them.

- Whether the PDF should be produced in a background job. WeasyPrint on a
  transcript of a two-hour interview has not been measured; if a request takes
  more than a few seconds, the PDF moves to a Celery task and the project's
  download directory, which changes UC-7 substantially.
- Whether subtitle formats need cue splitting, and by which rule. The current
  output is correct but hard to read for long segments.
- Whether TEI should carry mentions as `<persName>`, `<orgName>`, `<placeName>`
  and `<date>` inside the utterances. This is the natural home for the
  `mentions` map and the strongest argument for the TEI format existing at all,
  but it needs word-level markup inside `<u>`, which the current shape avoids.
- Whether an export should offer the speakers' colours anywhere. No format in
  this set has a place for them.
- Whether an administrator ever needs an unredacted derived format. The stored
  JSON download serves the unredacted content today, so the need would have to
  be for a specific format rather than for the content, and no such need is
  known.
- Whether `?speakers=0` should also strip the `speaker` key from the whisperX
  `word_segments` entries, which it does under the current design because the
  option clears the content, or whether whisperX consumers expect the key to be
  present with a placeholder value.
- Whether the interface should offer any option a format's row currently hides,
  in particular omitting speakers from CSV and TEI. The route already honours
  both, so this is a template change and no code change.

## Size assumption

Exports are built in memory and returned in one response. A three-hour interview
transcript is on the order of 40,000 words, which is a few megabytes of JSON and
well below a megabyte of VTT, CSV or TEI. The PDF is the only format whose
production time is not obviously small, which is why it is the last slice and
the subject of the first open question.
