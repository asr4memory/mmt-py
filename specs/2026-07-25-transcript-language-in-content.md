# Transcript language in the mmt content

This is an executable spec. It is the authoritative record of the decisions for
moving the transcript language out of the `Transcript` model column and into the
mmt-transcript JSON content. An implementing session works from this document
and resolves ambiguity by reading it.

## Motivation

The language of a transcript is a property of its content, not of the database
row. Keeping it in the JSON means it travels with the file on export and import,
and there is a single source of truth instead of a model column that can diverge
from the content. This also unblocks the ASR integration
([`2026-07-24-asr-app-integration.md`](2026-07-24-asr-app-integration.md)): the
ingest sets the detected language directly on the content it produces, with no
model field involved.

## Non-goals

- **No data migration of existing rows.** The format is still a beta version;
  the column is dropped without backfilling `content['language']`. Existing
  transcripts read back with `language` defaulting to `None` until they are next
  saved.
- **No schema version bump.** The field is added to `version: 1`; see the schema
  decision below.
- **No new language display in the editor.** The editor must preserve the
  language on save, but rendering it in the UI is out of scope here.
- **No change to the ASR transcribe form.** The auto-detect plus
  `WHISPERX_LANGUAGES` selector is owned by the ASR spec.

## Feature reference

### Schema

`language` is added to the pydantic `Transcript` in
[`app/mmt/transcripts/mmt_schema.py`](../app/mmt/transcripts/mmt_schema.py):

```python
language: str | None = None   # ISO 639-1 code; None when unknown
```

The field is optional with a `None` default, so it is an additive,
backwards-compatible change within `version: 1`: content stored before this
change has no `language` key and still validates (the default applies), and
content produced after it carries the key. The model keeps `extra='forbid'`; the
schema does not constrain the value to any fixed language set, because the
constraining of the input is the transcribe form's concern, not the schema's.

### Conversion

`_whisper_to_mmt` in
[`app/mmt/transcripts/normalize.py`](../app/mmt/transcripts/normalize.py)
currently drops the top-level `language` of the whisper input. It copies it into
the produced content:

```python
language = whisper.get('language')
if not isinstance(language, str):
    language = None
```

and adds `'language': language` to the result dict before `validate_mmt_content`.
WhisperX output carries a top-level `language`, so this is the same path for an
ASR result and a manual whisper paste. `validate_whisper_input` is unchanged;
the language is not required on the input side.

### Model

The `language` `CharField` and the `LANGUAGE_CHOICES` list are removed from the
`Transcript` model in
[`app/mmt/transcripts/models.py`](../app/mmt/transcripts/models.py). A migration
drops the column. There is no data migration.

### Manual upload form

`UploadedFileForm` in
[`app/mmt/uploaded_files/forms.py`](../app/mmt/uploaded_files/forms.py) drops
`'language'` from `Meta.fields`, so the manual upload no longer has a language
select. The language comes from the pasted or uploaded JSON's `language`
property, carried into the content by `normalize_content`. The
[`create_transcript.html`](../app/mmt/uploaded_files/templates/uploaded_files/create_transcript.html)
template renders the form fields one by one, so the language label and widget
block is removed from it as well.

### Transcript list

[`_transcript_table.html`](../app/mmt/uploaded_files/templates/uploaded_files/_transcript_table.html)
renders a Language column from `get_language_display`. The column is removed;
the language is not shown in the transcript list.

### NER task

`generate_transcript` in
[`app/mmt/transcripts/tasks.py`](../app/mmt/transcripts/tasks.py) drops the
`language=transcript.language` keyword when it creates the derived transcript.
`apply_mention_spans` returns the same content dict, so the source transcript's
`language` rides along in the content of the derived one.

### Admin

`language` is removed from `list_display`, `list_filter`, and the field list in
[`app/mmt/transcripts/admin.py`](../app/mmt/transcripts/admin.py).

### Endpoints

`detail_json` returns `transcript.content`, which now includes `language`, and
`update_json` validates the incoming content with `validate_mmt_content`, which
accepts the optional field. Neither view changes.

### Frontend

The editor sources the language from the fetched content instead of the
`data-language` attribute, and includes it in the save payload so it is not lost.

- [`assets/js/transcript/types.ts`](../app/assets/js/transcript/types.ts):
  `TranscriptContent` gains `language?: string | null`.
- [`assets/js/transcript/transcript_table.vue`](../app/assets/js/transcript/transcript_table.vue):
  `loadTranscript` reads `json.language` into a ref; `saveTranscript` includes
  `language` in the `updateTranscript` payload; the value passed to `DocumentBar`
  comes from that ref.
- [`assets/js/transcript.ts`](../app/assets/js/transcript.ts): the
  `language: readString(container, "language")` prop is removed.
- [`app/mmt/transcripts/templates/transcripts/edit.html`](../app/mmt/transcripts/templates/transcripts/edit.html):
  the `data-language="{{ transcript.language }}"` attribute is removed.

## Slices and tasks

Each slice leaves the system working and independently deployable.

- [x] **1 Schema and conversion.** (2026-07-25) Add `language` to the mmt schema and carry it
  through `_whisper_to_mmt`. Done when `tests/test_normalize.py` asserts a
  whisper input's `language` appears in the produced content and an absent one
  yields `None`, and the schema tests accept both content with and without the
  key. The existing `test_drops_unknown_whisper_keys` keeps only the
  `word_segments` drop; the language assertion moves to the carry-through test
  above.
- [x] **2 Frontend round-trip.** (2026-07-25) Load `language` from the content, include it in
  the save payload, and add it to `TranscriptContent`. Done when a vitest test
  shows a loaded transcript's `language` is present in the payload passed to
  `updateTranscript` after a save, unchanged by editing.
- [x] **3 Remove the model field.** (2026-07-25) Drop `Transcript.language` and
  `LANGUAGE_CHOICES`, the form field, the admin entries, the NER task keyword,
  and the `data-language` template attribute with its `readString` prop; add the
  column-drop migration. Done when the backend tests pass, a manual upload's
  stored content takes its `language` from the pasted JSON, and a NER-derived
  transcript keeps the source language in its content. Existing tests are updated
  for the removed field: `test_tasks.py` drops the `language=` create keywords
  and checks `content['language']` for NER propagation, `test_views.py` and
  `test_normalize_transcripts_command.py` drop the `language=` keyword, and the
  manual-upload tests in `uploaded_files/tests/test_views.py` drop the stale
  `language` POST field and assert the stored language comes from the pasted
  JSON.
