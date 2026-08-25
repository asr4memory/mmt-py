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
speakers list, an entities map, a mentions map and a redactions map:

```jsonc
{
  "format": "mmt-transcript",   // identity — what loaders match on
  "version": 1,                 // schema revision — integer, what migrations compare
  "speakers": [
    { "id": "s1", "name": "Alice", "color": "#5b9bd5" }
  ],
  "entities": {
    "ent_9c2f": { "name": "Angela Merkel", "type": "PER",
                  "aliases": ["Merkel"], "wikidataId": "Q567" }
  },
  "mentions": {
    "men_7f3a": { "label": "PER", "score": 0.93, "entityId": "ent_9c2f" }
  },
  "redactions": {
    "red_4b1e": { "reason": "Names the employer", "start": null, "end": null }
  },
  "segments": [
    {
      "id": "seg_a1", "start": 0.0, "end": 4.2, "speakerId": "s1",
      "words": [
        { "id": "w_x9", "start": 0.0, "end": 0.3, "word": "Hi",
          "score": 1.0, "speakerId": "s1", "mentionId": null,
          "redactionId": null }
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
- **An occurrence tier, not an identity tier.** The identity tier is the
  separate `entities` map below; a mention points at one entry of it through
  its `entityId`.

### Entities

An entity is one *identity* the transcript talks about — the person "Angela
Merkel" that three mentions of that name and one mention of "Merkel" all refer
to. Entities live in a transcript-level `entities` map keyed by entity id
(`ent_<uuid>`), following the mentions pattern, and their scope is one
transcript. A real DB entity is deferred until identity has to be shared across
transcripts, by the same reasoning that defers a `Speaker` entity.

- **Value shape:**
  `{ "name": "Angela Merkel", "type": "PER" | "ORG" | "LOC",
  "aliases": ["Merkel"], "wikidataId": "Q567" }`.
- **`name`** is the canonical label. It is not called `label`, because
  `mention.label` means something else; `type` is named for the same reason.
- **`type` has no `DATE`.** A date has no identity; making a date canonical
  means normalising it to a calendar value, which would be a field on the
  mention rather than an entry here.
- **`aliases`** are further surface forms the entity is matched by, and default
  to an empty list. **`wikidataId`** is `Q` followed by digits, or `null`.
- **Mentions link via `entityId`** (nullable, like `mentionId` on a word).
  `null` is a legal permanent state: linking is a separate step from creating a
  mention, and an unlinked mention is not an unfinished one.
- **`mention.label` and `entity.type` may differ.** The label is the NER pass's
  raw claim and is kept as provenance; the type is the user's decision about the
  identity. The validator does not force them to agree.
- **Relational invariants** (enforced by the strict validator): entity ids share
  the document-wide id namespace, every non-null `entityId` resolves to an
  `entities` entry, and every entity is referenced by at least one mention —
  editors must garbage-collect entities that lose their last mention, as they
  already do for mentions that lose their last word.
- **Added within `version: 1`, without compatibility for documents stored
  before it.** The `entities` map is required, like `speakers` and `segments`,
  so a document written before the field existed does not validate. No upgrade
  path is provided: `normalize_content` re-validates content that already
  carries `format: "mmt-transcript"` rather than upgrading it, so
  `normalize_transcripts` reports such a row as invalid and skips it. The
  format is in its development phase and breaking stored content is cheaper
  here than carrying a default whose only purpose is to accept the old shape.
  Once the format leaves that
  phase, an additive change to an `extra: forbid` schema is a version-bump
  event and stored documents are migrated rather than broken.
- **`entityId` is defaulted, not required**, in the same way as `score` on a
  mention and `speakerId` and `mentionId` on a word: an absent key means
  `null`, which is the state of an unlinked mention.

### Redactions

A redaction is one contiguous run of words that must not be published, plus an
optional reason recording why. Redactions live in a transcript-level
`redactions` map keyed by redaction id (`red_<uuid>`), following the mentions
pattern. They are a second occurrence tier beside the mentions, not above or
below them: the mention tier records which words are a name and what kind of
name the model thought it was, the redaction tier records which words must not
be published and why. Neither is derived from the other.

- **Value shape:**
  `{ "reason": "Names the employer", "start": null, "end": null }`.
- **`reason`** is free text or `null`. An empty string is legal; the field
  exists for the user, not for the format.
- **Words link via `redactionId`** (nullable, like `mentionId`). A word belongs
  to at most one redaction.
- **`redactionId` and `mentionId` are independent.** A word may carry both, one
  or neither, and a redaction may cover part of a mention, all of it, or several
  mentions at once. The validator enforces no relationship between the two, and
  re-running named-entity recognition rebuilds the mention tier while leaving
  the redaction tier untouched.
- **Relational invariants** (enforced by the strict validator): redaction ids
  share the document-wide id namespace, every non-null `redactionId` resolves to
  a `redactions` entry, and every redaction is referenced by at least one word —
  editors must garbage-collect a redaction when its last word is unlinked, as
  they already do for mentions and entities.
- **Two invariants the mention tier does not have:** the words of one redaction
  lie in a single segment, and they occupy consecutive positions in that
  segment's word list. The reason is the derived time range described below: the
  marked words and the silenced range only describe the same passage when the
  words are one uninterrupted run inside one segment. A gap means a word that is
  published in the text while its audio is silenced; a run crossing a segment
  boundary silences everything between the two segments, including another
  speaker's words that nobody marked.
- **The time range** a redaction covers is the `start` of its first word and the
  `end` of its last word. `start` and `end` on the redaction itself are inert in
  this version: they are validated and carried through, but nothing writes them.
  When they are set they override the range derived from the words. Because
  every redaction must be referenced by at least one word, a region containing
  no words cannot be redacted.
- **Applying a redaction is separate work** and no part of the application does
  it yet. The rule is fixed nevertheless, because it is the retroactive meaning
  of every redaction stored under this version: applying one replaces each
  linked word's `word` value with the marker `XXX`, keeping its `id`, `start`,
  `end` and `speakerId` and clearing its `mentionId` and `redactionId`, and
  silences the effective range in the media.
- **A redaction is not access control.** The unredacted words stay in
  `Transcript.content` and every user who may open the transcript reads them.
- **Added within `version: 1`, without compatibility for documents stored
  before it**, on the same grounds as the `entities` map. The `redactions` map
  is required, so a document written before the field existed does not validate
  and is reported as invalid by `normalize_transcripts` rather than repaired.
  `redactionId` on a word, and `reason`, `start` and `end` on a redaction, are
  defaulted rather than required: an absent key means `null`, which is the state
  of a word nobody redacted.

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
