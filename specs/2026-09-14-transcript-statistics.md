# Transcript statistics on the detail and list pages

This is an executable spec. It is the authoritative record of the decisions for
showing numbers derived from the mmt-transcript content on the transcript detail
page and in the transcript table of an uploaded file. An implementing session
works from this document and resolves ambiguity by reading it.

## Motivation

The content holds facts a user wants to see without opening the editor: which
language and model produced the transcript, how long it is, and how much of it
is marked as an entity or a redaction. Both pages currently defer the content
column, which is the property worth keeping: the detail page can afford to load
one document, a list of transcripts cannot afford one per row.

## Non-goals

- **No derived columns and no stored statistics.** Nothing is written to the
  database, so no value can be stale and no migration is needed. The two use
  cases are display only; filtering, sorting and aggregating across transcripts
  are not supported and would be the trigger to revisit this decision.
- **No change to the read-only API.** `TranscriptOut` keeps the fields
  [`2026-07-30-read-only-api.md`](2026-07-30-read-only-api.md) specifies, and
  its open question about denormalised columns stays open.
- **No word count on the list page.** See the decision below.

## Feature reference

### The derived values

`app/mmt/transcripts/statistics.py` holds one function:

```python
def derive_statistics(content) -> dict:
    """Numbers derived from mmt-transcript content, for display."""
```

It returns exactly these keys, read with `.get()`:

| Key | Value |
| --- | --- |
| `language` | `content['language']` |
| `model` | `content['model']` |
| `speaker_count` | `len(content['speakers'])` |
| `segment_count` | `len(content['segments'])` |
| `word_count` | the number of word objects over all segments |
| `mention_count` | `len(content['mentions'])` |
| `entity_count` | `len(content['entities'])` |
| `redaction_count` | `len(content['redactions'])` |

Every value is `None` when the content is not a mapping or the key is absent, so
a count of `0` means the document has none and `None` means the document predates
the mmt format. The function never raises on malformed content.

### Detail page

[`transcripts/views.py`](../app/mmt/transcripts/views.py) `detail` drops
`.defer('content')` and puts `derive_statistics(transcript.content)` into the
context as `statistics`.
[`transcripts/_metadata.html`](../app/mmt/transcripts/templates/transcripts/_metadata.html)
renders one `dt`/`dd` pair per value, above the existing timestamps, labelled
Language, Model, Speakers, Segments, Words, Mentions, Entities and Redactions. A
`None` renders as an em dash.

### List page

[`uploaded_files/views.py`](../app/mmt/uploaded_files/views.py) `detail` keeps
`.defer('content')` and calls a new queryset method on `Transcript`:

```python
class TranscriptQuerySet(models.QuerySet):
    def with_statistics(self):
        """Annotate the values the transcript table shows, so the list does
        not have to load the content column."""
```

It annotates `language` and `model` with `KeyTextTransform`, and `segment_count`
with `Func(F('content'), Value('$.segments'), function='JSON_LENGTH')`. MySQL
returns `NULL` for an absent path, which matches the `None` of the Python
function. Adding the manager needs no migration.

[`_transcript_table.html`](../app/mmt/uploaded_files/templates/uploaded_files/_transcript_table.html)
gains Language, Model and Segments columns between Label and Created at, each
rendering an em dash when the value is `NULL`.

### Pinned decisions

- **MySQL-specific SQL is acceptable.** Development, test and production all run
  MySQL, so `JSON_LENGTH` needs no cross-backend fallback.
- **The list page shows three of the eight values.** The table already scrolls
  sideways on a narrow screen, so it takes only the values that identify the
  transcript and its length. The remaining counts are detail-page only.
- **The word count is not annotated.** Counting words per segment needs
  `JSON_TABLE`, which does not belong in a queryset annotation. The detail page
  computes it in Python, where it is one loop.

## Slices and tasks

- [x] **1 Detail page.** (2026-09-14) Add `statistics.py`, drop the defer in
  `transcripts.views.detail`, and render the eight values in the metadata
  sidebar. Done when `tests/test_statistics.py` asserts the values for the
  `export_content` fixture and asserts that `{}` yields every value as `None`,
  and a view test finds the segment and word counts in the rendered detail page.
- [x] **2 List page.** (2026-09-14) Add
  `TranscriptQuerySet.with_statistics()` and the three columns. Done when a
  test asserts the annotated values of a stored transcript equal the
  corresponding values of `derive_statistics` for the same content,
  that the annotations are `None` for a row whose content is `{}`, and that the
  transcripts in the uploaded file detail context still report `content` in
  `get_deferred_fields()`.
