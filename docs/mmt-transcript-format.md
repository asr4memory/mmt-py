# mmt-transcript format

Status: **draft / living document**

This note captures the design intent behind mmt's own transcript format: an
enriched superset of Whisper/whisperX output that the transcript editor reads
and writes. It records the *why*; the eventual JSON Schema (see
[Schema](#schema)) is the machine-checkable *what*.

## Goals

- Persist everything Whisper gives us, **plus** the data the editor produces
  (stable IDs, speaker identity, display names, colors, edits).
- More data than too little: we can always transform back down to plain Whisper
  later. The reverse (recovering data Whisper never had) is impossible.
- Stay file-based for now — a JSON blob in `Transcript.content`
  (`app/mmt/transcripts/models.py`). **No dedicated DB tables yet.** A real
  `Speaker` entity is deferred until a feature genuinely needs cross-transcript
  or unattached-speaker identity.

## Format shape

A superset of Whisper, with two top-level identity fields, a persisted
speakers list, and a mentions map:

```jsonc
{
  "format": "mmt-transcript",   // identity — what loaders match on
  "version": 1,                 // schema revision — integer, what migrations compare
  "speakers": [
    { "id": "s1", "name": "Alice", "color": "#5b9bd5" }
  ],
  "mentions": {
    "men_7f3a": { "label": "PER", "score": 0.93 }
  },
  "segments": [
    {
      "id": "seg_a1", "start": 0.0, "end": 4.2, "speakerId": "s1",
      "words": [
        { "id": "w_x9", "start": 0.0, "end": 0.3, "word": "Hi",
          "score": 1.0, "speakerId": "s1", "mentionId": null }
      ]
    }
  ]
}
```

### Why these choices

- **`format` and `version` are separate fields.** `format` answers "what kind
  of file is this?"; `version` answers "which revision of that shape?". Fusing
  them (`"mmt-1"`) would force readers to string-split before a numeric
  `version >= 2` check. Keep `version` a clean integer.
- **`format: "mmt-transcript"`** is namespaced (not bare `"mmt"`) so a future
  second file type doesn't need a retrofit disambiguator.
- **Segments carry no `text` field.** Whisper puts the segment's text next to
  its words, which is a second copy of the same content that goes stale as soon
  as a word is edited, deleted or marked for redaction. The words are the only
  representation of what was said; a consumer that needs a segment's text joins
  the words with a space. The strict validator rejects the key because unknown
  keys are forbidden.
- **Optional provenance** can be added later as its own field (e.g.
  `producer: "mmt 0.4.2"`) — "which build wrote this", distinct from both
  identity and schema version. Do not overload `format`/`version` for it.
- **Speakers are a persisted top-level array keyed by `id`**, referenced from
  segments/words via `speakerId`. This is what makes rename O(1), persists
  colors, and lets an unassigned speaker exist in the file (fixing the
  phantom-speaker quirk where the speaker list is re-derived from segment
  strings on every load).

### Mentions

A mention is one *occurrence* of a named entity in the transcript — "Angela
Merkel" said twice is two mentions. They live in a transcript-level
`mentions` map keyed by mention id (`men_<uuid>`), mirroring the speakers
pattern: entity-occurrence data lives in one place, words point at it.

- **Value shape:** `{ "label": "PER" | "ORG" | "LOC" | "DATE", "score": 0.93 }`.
- **`score`** is a confidence in `[0, 1]`: the NER model's span confidence,
  stored raw and unfiltered (one score per span, no aggregation across the
  span's words). Filtering by threshold is a display concern, not a format
  concern. The schema default is `1.0` for mentions that no scoring process
  produced (e.g. manually created ones).
- **Words link via `mentionId`** (nullable, like `speakerId`). A word belongs
  to **at most one** mention — the NER pipeline guarantees non-overlapping
  spans, so readers never arbitrate. A multi-word mention is consecutive words
  sharing one `mentionId`; mentions may span segment boundaries.
- **Relational invariants** (enforced by the strict validator): every
  `mentionId` resolves to a `mentions` entry, and every mention is referenced
  by at least one word — editors must garbage-collect orphaned mentions on
  delete rather than leave them dangling.
- **Provenance:** mentions are minted app-side. The NER service is
  format-agnostic (`POST /extract`, word batches in, word-index spans with
  scores out — see `ner/README.md`); the app materialises those spans into
  this map.
- **Deliberately an occurrence tier, not an identity tier.** A future global
  `entities` map (mentions → entity id, entities carrying e.g. Wikidata QIDs)
  would layer identity on top; since `extra: forbid` rejects unknown keys,
  adding it is a `version: 2` event.

### IDs must be stable and unique

The current in-memory IDs (`assets/js/helpers/add_ids_to_transcript.js`) are
**positional indices**, reset per load and only unique within a segment for
words. They are unsuitable to persist — the whole point of a persisted ID is
that it survives edits and reloads.

- Use genuinely unique, stable IDs: `crypto.randomUUID()` / nanoid, or a
  file-stored monotonic counter.
- Newly inserted segments/words (`insertSegmentBefore` etc.) must get fresh
  unique IDs from the same scheme, not placeholders like `"newSeg"`.
- The display number (`#003`) becomes a computed positional index, **decoupled**
  from the stable `id`.

## Validation strategy

Validate at trust boundaries, with **opposite strictness** on each side:

- **Whisper input (ingestion): lenient.** Validate only what the editor depends
  on; goal is a clear, fail-fast error, not exhaustive conformance. Whisper
  output varies (plain vs whisperX, optional word timestamps, optional
  diarization).
- **mmt format (on save / on read): strict.** It is our own contract; enforce
  the invariants the system relies on.

### Current hard requirement: word-level timestamps

The editor is **word-timestamp only** today — it edits timecodes per word
(`updateTimecode` keys on `wordId`; `insertLeft`/`insertRight` compute per-word
offsets). So the Whisper-input schema currently **requires** non-empty
`words[]` with numeric `start`/`end` per word.

- Keep `speaker` **optional** even while strict on timestamps — diarization is a
  separate flag and the editor copes with its absence.
- The rejection message must name the actual cause, e.g. *"This transcript has
  no word-level timestamps; the editor currently requires them (e.g. whisperX
  output)."*
- "Strict now, loosen later" is the safe direction: loosening a schema is
  backward-compatible; tightening is breaking. **But** relaxing the
  word-timestamp requirement is also *editor* work (rendering/editing
  segment-only transcripts), so the schema requirement should move **with**
  editor capability, never ahead of it.

### Tooling

- `jsonschema` (Python) for **structure** (types, required, enums, formats).
  Not yet a dependency — would be added to `app/pyproject.toml`.
- jsonschema **cannot** express referential integrity ("every `speakerId`
  resolves to a `speakers[]` entry") or cross-array uniqueness ("word ids unique
  across all words in all segments"). Pair the schema with a small amount of
  Python for those relational checks.

## Migration strategy

Migration runs in the **Python backend**, since `content` is a JSONField the
backend owns. Two complementary moves:

1. **Enrich at ingestion.** Normalize Whisper JSON to the mmt format where it
   first lands in `content`. New transcripts are *born* enriched and never need
   legacy detection.
2. **One-time bulk upgrade** for existing rows — a management command (preferred
   over a data migration, which freezes as historical code) that runs the same
   idempotent transform.

Keep the transform a plain, unit-tested, version-aware function:

```python
def normalize_content(content):
    version = content.get("version", 0)
    if version < 1:
        content = _upgrade_v0_to_v1(content)  # mint ids, build speakers[], map refs
    # if version < 2: ...
    return content
```

Call it from both ingestion and the management command. The `version` check
makes re-runs no-ops (idempotent).

### Consequence: the frontend migration can be deleted

Once enrichment is server-side, `addIDsToTranscript`, load-time
`extractSpeakers`, and strip-on-save (`removeIDsFromTranscript`) leave the
hot path. The Vue app receives the canonical format and saves it back unchanged.

**The one job that stays client-side:** minting IDs for segments/words created
*during a live edit*. The server isn't in the loop for those, so use a scheme
the client can generate collision-free without coordination (uuid/nanoid). The
backend trusts and persists them (and may validate uniqueness on write).

## Schema

When built, the JSON Schema lives alongside this doc, versioned together:

- `docs/schema/mmt-transcript.v1.json` (and `v2`, … as `version` bumps)
- Doubles as documentation, a migration-test oracle (assert
  `normalize_content(legacy)` output conforms), and a frontend type source
  (`json-schema-to-typescript`) — which would remove the duplicated
  `{ name, color }[]` casts in the Vue components.

## Open questions

- **Canonical speaker location** for the back-to-Whisper exporter: speaker on
  segments vs words. whisperX carries it on words and/or segments; pick one
  (segment-level is simpler; words inherit) so the round-trip is unambiguous.
- **Rename collision behavior** beyond the current reject: support
  merge-on-collision (renaming A→B where B exists folds A into B)?
- **When to introduce a real `Speaker` DB entity** (the deferred option 2):
  triggered by a speaker library across transcripts, per-speaker analytics, or
  persistent unattached speakers.
- **Session-only vs persisted IDs** transition order — start by persisting IDs
  in the file format; revisit if a DB entity later changes ownership of identity.
