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
inverse function anywhere in the codebase, and none is planned. With redactions
applied it is not even information-preserving in principle: the marker `XXX`
replaces words that the export does not carry anywhere. Data enters a
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

## No format is ever held as data

There is no registry, no format table and no mapping from a format key to
anything. A format key appears in a URL path, in a route name, in a view name and
in a template, and nowhere as a value a lookup is performed on.

The mechanism is one route and one view per format, each view a single call into
a shared `_export` helper that names the format's exporter, extension and content
type as arguments:

```python
@require_GET
@permission_required('transcripts.view_transcript')
def export_vtt(request, pk):
    return _export(request, pk, vtt.export, 'vtt', 'text/vtt; charset=utf-8')
```

Everything about WebVTT is then reachable by following the route to the view to
`vtt.py`, with nothing to resolve in between. The format's name, its description
and the export options its row offers are in `detail.html` as `{% translate %}`
strings, next to the other user-visible text of this application. A format is
named in the URLconf, in one view, in one exporter module and in the template.

The alternative, and the shape this document described first, is a table keyed
by the format key that the view resolves and the template renders. It costs one
level of indirection on every reading of the code and buys a cheaper seventh
format. The set of formats is close to fixed: once the six in the spec exist, a
year can pass without a seventh, and adding one is four small edits either way.
Six near-identical view functions with repeated decorators is the price, and it
is the cheaper of the two.

Per-format options did not change this. Because both options are content
transformations, no format can be wrong about an option and there is nothing for
a table to enforce; the rows differ only in which controls are worth showing,
which is a question the template answers. What would change it is a rendering
option a format must reject rather than ignore, or an option set large enough
that six hand-written forms stop being readable. A structure driving both the
form rendering and the validation would then be the right answer, and introducing
it is a mechanical change over code that already has the right seams. It is not
built before it is needed.

## Options transform the content, not the output

An export option could be built two ways: as a parameter an exporter reads while
it writes, or as a transformation of the content the exporter is given. Both
options this feature has are built the second way, and the preference is
deliberate.

Applying redactions replaces the redacted words with a marker in the model.
Omitting speakers clears every `speakerId` and empties the speakers list in the
model. In both cases the exporter receives a transcript that is a legal
mmt-transcript document and writes it the way it writes any other. Every format
already had to specify what it emits for a segment without a speaker; the option
produces exactly that input.

Three things follow:

- **No exporter knows an option exists.** There is no option parameter on
  `ExportContext`, no branch inside a format writer, and no format that can be
  wrong about an option. `_export` applies both transformations once, before it
  calls whichever exporter its caller named, so adding a format costs nothing in
  option handling.
- **Every combination is valid for every format**, so the route can honour any
  option for any format. Which controls a format's row shows on the detail page
  is a judgement about what is worth offering, not a constraint, and it lives in
  the template rather than in a table the view consults.
- **The transformations are testable on their own**, as functions from a
  transcript to a transcript, without reference to any format.

A rendering option, such as a subtitle line length, cannot be built this way and
would have to reach the exporters that implement it. That is the point at which
`ExportContext` grows an options field. Nothing about the transformations
changes when it does; the two kinds coexist.

`apply_redactions` lives in `mmt/transcripts/redact.py` rather than in the
export package, beside `normalize.py` and its `apply_mention_spans`. It
implements the rule pinned in the redactions spec, and the work that produces
redacted media will want it without importing anything export-shaped.

The transformation must produce a *validated* model, not a mutated one. Applying
redactions clears `redactionId` and `mentionId` on the affected words, which
orphans entries the schema requires to be referenced, so the transformation also
drops the redactions, the newly unreferenced mentions and the entities left
without one. Building the result through validation is what turns a missed step
into one error rather than an invalid document reaching a format writer.

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
3. Add `export_<key>` to `views.py`, a single call into `_export` naming the
   exporter, the extension and the content type.
4. Add its route to `urls.py` as `export-<key>`.
5. Add the row — the form, the name, the description, the download button and
   a disclosure including whichever option partials the format should offer — to
   the export section of `detail.html`.
6. Add the German translations to `locale/de/LC_MESSAGES/django.po` and run
   `compilemessages`.
7. State in the spec's "What each format carries" table what the format keeps
   and what it drops.
