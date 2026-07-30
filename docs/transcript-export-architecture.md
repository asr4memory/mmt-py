# Transcript export architecture

Status: **draft**, written alongside
[`specs/2026-07-30-transcript-export.md`](../specs/2026-07-30-transcript-export.md).

This note records where transcript export sits in the application and why it is
built the way it is. The spec records what is built for the first set of
formats; this note records the structural decisions that outlive any single
format.

## Position in the application

The stored transcript is one JSON document in `Transcript.content`, in the
mmt-transcript format described in
[`mmt-transcript-format.md`](mmt-transcript-format.md). That document is the
authoritative record: it is what the editor reads and writes, and it is designed
to hold more than any consumer needs, on the principle that data can always be
dropped later and never recovered later.

Export is the layer that drops what a particular consumer does not need.

```
                     +-------------------------+
                     |   Transcript.content    |
                     |   (mmt-transcript JSON) |
                     +------------+------------+
                                  |
                        normalize_content()
                                  |
                     +------------v------------+
                     |  mmt_schema.Transcript  |
                     |   (validated model)     |
                     +------------+------------+
                                  |
                          ExportContext
                                  |
        +------------+------------+------------+------------+
        |            |            |            |            |
   +----v----+  +----v----+  +----v----+  +----v----+  +----v----+
   | whisperx|  |  vtt/srt|  |   csv   |  |   tei   |  |   pdf   |
   +---------+  +---------+  +---------+  +---------+  +---------+
        |            |            |            |            |
        +------------+------------+------------+------------+
                                  |
                          bytes, one response
```

Export is **one-way**. No exported format can be read back in; there is no
inverse function anywhere in the codebase, and none is planned. Data enters a
transcript through the ASR ingest and the editor, both of which produce the mmt
format directly. This is what lets an exporter be lossy without anybody having
to reason about what a round trip would preserve.

## Exporters are pure functions

An exporter takes an `ExportContext` and returns `bytes`. It does not touch the
database, the request, the session, the filesystem or the current user. Three
consequences follow, and they are the reason for the shape:

- **Tests need no database and no client.** An exporter test builds a context
  from a fixture and asserts on the returned bytes. Only the view's own test
  needs `django_db`.
- **A format's rules live in one file.** Everything the VTT output depends on is
  in `vtt.py`; there is no template, no view branch and no model property
  contributing to it.
- **Another caller is possible later without changing the exporters.** A
  management command, a background job or a different transport can build a
  context and call the same function. Nothing in the exporters assumes an HTTP
  request exists.

`bytes` rather than `str` is deliberate. The PDF has no string form, the CSV
needs a byte order mark for Excel, and the XML serialiser writes its own
encoding declaration. If exporters returned strings, the view would have to know
each format's encoding, which is exactly the knowledge that belongs to the
format.

## The registry is the extension point

`EXPORT_FORMATS` maps a URL key to an `ExportFormat` holding the format's name,
description, extension, content type and export function. It is read in two
places: the view resolves the requested key, and the transcript detail page
renders the list of links.

Adding a format is therefore one new module and one registry entry. It is not a
template change, not a view change and not a URL change. Any code that hardcodes
a format key outside `registry.py` and the exporter modules has broken the
pattern.

The registry deliberately holds display strings. Keeping the name and the
description next to the exporter that produces the file means a format cannot be
listed in the interface as something other than what it emits.

## Exporters read the validated model, not the raw dict

The view calls `normalize_content` and hands the resulting
`mmt_schema.Transcript` to the exporter. The raw `content` dict never reaches an
exporter.

The dict form invites a whole class of quiet failure: `segment.get('speakerId')`
returns `None` both for a segment without a speaker and for a key that a schema
change renamed, and `segment['words']` on content stored before a field existed
raises deep inside a format writer. The validated model turns both into a single
failure at one point, before any output is produced, where the view can report it
as "this transcript cannot be exported" rather than emitting a half-written file.

Using `normalize_content` rather than `validate_mmt_content` also means legacy
whisper-shaped content, stored before the mmt format existed, exports correctly.
The normalised form is not written back: an export is a read, and a request that
a user believes to be a download should not migrate their data as a side effect.

## Every format is lossy, and the mmt download stays

The mmt-transcript document holds word timings, confidence scores, stable
identifiers, speaker colours and the mentions map. No format in the first set
carries all of it, and no future format is expected to. The spec states, per
format, what survives.

The consequence is that the existing "Download JSON" link, which serves the
stored mmt content unchanged, is not part of the export section and is not
replaced by one of its formats. It is the only download that loses nothing, and
it is the one an administrator or a future version of this application reads
back.

## Segment text has exactly one definition

A segment carries no `text` field, by a decision recorded in
[`mmt-transcript-format.md`](mmt-transcript-format.md): a stored copy of the text
goes stale as soon as a word is edited. Every format that needs a segment's text
therefore derives it the same way, by joining the segment's words with a single
space.

That rule is stated once in the spec and implemented independently in each
exporter, which is a small duplication accepted on purpose: a shared
`segment_text()` helper would become the place where a future format's special
casing accumulates, and a format's text assembly is part of that format's
definition.

## Synchronous and in memory

An export is produced inside the request and returned in one response. There is
no Celery task, no file written to the project's download directory and no
caching of results.

The reason is the size of the input: a transcript is text, and even a long
interview is a few megabytes of JSON and far less in any of the text formats.
The one output whose production cost is not obviously small is the PDF, since
WeasyPrint lays out the whole document; that is an explicit open question in the
spec, and it is the only format expected to move to a background job.

Nothing about the exporter interface changes if it does. A pure function from a
context to bytes is exactly what a Celery task calls.

## Encoding

UTF-8 everywhere, with two deliberate exceptions to the plain form:

- CSV is written as `utf-8-sig`, with a byte order mark, because Excel reads a
  UTF-8 CSV without one in the system's legacy encoding and displays umlauts
  incorrectly. Spreadsheet use is the reason the format exists, so the format
  follows the spreadsheet.
- XML is serialised by `xml.etree.ElementTree` with an encoding declaration, so
  the declaration and the actual bytes cannot disagree.

JSON is written with `ensure_ascii=False`, so an exported German transcript is
readable in an editor rather than a wall of `ä`.

## Escaping belongs to the format

Each format states its own escaping rule and implements it, or delegates it:

- TEI hands escaping to `ElementTree`, which is the only reliable way to get XML
  escaping right.
- VTT escapes `&`, `<` and `>` in cue text and voice tags, because those three
  characters are markup in VTT.
- CSV hands quoting to the standard library's `csv` writer, which implements
  RFC 4180.
- SubRip escapes nothing, because SubRip text is plain text.

No exporter alters the transcript's characters to avoid an escaping problem. If
a text cannot be represented without escaping, it is escaped; it is never
rewritten.

## Adding a format

1. Write the tests first, against a context built from the shared fixture.
2. Add `exporters/<key>.py` with `export(context) -> bytes`.
3. Add the entry to `EXPORT_FORMATS`, with a translated name and description.
4. Add the German translations to `locale/de/LC_MESSAGES/django.po` and run
   `compilemessages`.
5. State in the spec's "What each format carries" table what the format keeps
   and what it drops.

There is no step involving the view, the route or the template.
