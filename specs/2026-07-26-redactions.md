# Redacted and anonymized sections in the mmt-transcript format

This is an executable spec. It is the authoritative record of the decisions for
recording redacted and anonymized passages in the mmt-transcript content and for
the editor operations that create and edit them. An implementing session works
from this document and resolves ambiguity by reading it.

## Motivation

Interviews contain names, places and whole passages that must not be published.
That decision is editorial: a person makes it once while working in the
transcript editor, and it has to persist with the transcript so that every later
export can apply it. Today the editor can mark a word as a named-entity mention,
but there is nothing that records "this passage must be removed" or "this name
must be replaced".

The mentions map already solves the structural half of this problem: an
occurrence-level record lives in one transcript-level map, and the words that
belong to it point at it by id. Redactions reuse that shape. The differences
from mentions are that a redaction carries an editorial instruction rather than a
classification, that it also concerns the media and not only the text, and that a
word can belong to a mention and to a redaction at the same time — the common
case is redacting a name that the NER pass already marked as a `PER` mention.

## Non-goals

- **No application of the redaction.** This spec records the marks only.
  Producing a silenced media file, a redacted text export or a redacted copy of
  the transcript is separate work, and the format is deliberately designed so
  that work can happen later without another schema change.
- **No access control.** A redaction does not change who may read the
  transcript. The unredacted words stay in `Transcript.content` and every user
  who can open the editor sees them.
- **No pseudonym identity.** Giving the same person the same replacement text
  across all their occurrences is an identity problem, which
  [`docs/canonical-entities-plan.md`](../docs/canonical-entities-plan.md)
  designs. A `replacement` here applies to one redaction only. When entities
  land, a consistent pseudonym belongs on the entity, and this field stays the
  per-occurrence override.
- **No automatic redaction.** A batch action such as "redact every `PER`
  mention" is deferred; see the open questions.
- **No redaction overview UI.** There is no drawer or panel listing all
  redactions of a transcript. Every operation happens in the word popover.
- **No schema version bump.** The fields are additive with defaults, so this
  extends `version: 1` in place, on the same grounds as the entities plan.

**Known limitation, not addressed here:** `Segment.text` duplicates the words and
is not regenerated when words change, so a text export that reads `text` instead
of `words` would show unredacted content. Any future export must build its text
from `words`.

## Feature reference

### Concept

A **redaction** is one contiguous run of words that must not be published, plus
the instruction for what to do with it. Removing a passage and replacing a name
with a pseudonym are the same kind of editorial mark with a different
instruction, so they are one concept with a `mode` field rather than two parallel
top-level maps:

- `mode: 'remove'` — the passage is taken out. A text export drops it, a media
  export silences the range.
- `mode: 'replace'` — the passage is substituted with `replacement`. A text
  export prints that string; what a media export does with it is that export's
  decision (silence is the expected default).

The words fix **which text** the redaction affects. The optional `start` and
`end` fields fix **which audio** it affects, and override the range derived from
the words.

### Schema

Added to [`app/mmt/transcripts/mmt_schema.py`](../app/mmt/transcripts/mmt_schema.py):

```python
RedactionId = Annotated[str, StringConstraints(min_length=1)]


class Redaction(BaseModel):
    model_config = ConfigDict(extra='forbid')

    mode: Literal['remove', 'replace'] = 'remove'
    replacement: str | None = None
    reason: str | None = None
    start: float | None = Field(default=None, ge=0)
    end: float | None = Field(default=None, ge=0)

    @model_validator(mode='after')
    def _consistent(self):
        if self.mode == 'replace' and not self.replacement:
            raise ValueError('replace redaction needs a replacement')
        if self.mode == 'remove' and self.replacement is not None:
            raise ValueError('remove redaction must not carry a replacement')
        if (self.start is None) != (self.end is None):
            raise ValueError('redaction needs both start and end or neither')
        if self.start is not None and self.start > self.end:
            raise ValueError('redaction: start after end')
        return self
```

`Word` gains `redactionId: str | None = None`, next to and independent of
`mentionId`. `Transcript` gains `redactions: dict[RedactionId, Redaction] = {}`.

The relational invariants in `Transcript._relations` mirror the mention ones
exactly: redaction ids are claimed into the same `seen_ids` set, so they are
unique against every speaker, mention, segment and word id; every `redactionId`
on a word resolves to a `redactions` entry; and every redaction is referenced by
at least one word, so editors garbage-collect a redaction when its last word is
unlinked. The error messages follow the existing wording: `word {id}: unknown
redactionId {value!r}` and `orphaned redaction {id!r}: no word references it`.

Two things are deliberately **not** enforced, matching how mentions are handled:
the words of one redaction are not checked for contiguity, and there is no
constraint between `mentionId` and `redactionId` on a word. A word may carry
both, one, or neither, and a redaction may cover part of a mention.

### The time range

The effective range of a redaction is the `start` of its first word and the `end`
of its last word, unless `start` and `end` are set on the redaction, in which case
those win. The reasons for the override are that word timestamps from ASR are
approximate, and that the audio between two words — a pause, a breath, a
half-spoken name — is not covered by any word's range. Padding around the range
is an export-time decision and is not stored.

Because every redaction must be referenced by at least one word, a region that
contains no words at all cannot be redacted. That is accepted for this version;
see the open questions.

### IDs

Redaction ids use the existing scheme with the prefix `red`: `_new_id('red')` on
the backend, `newId("red")` in the store.

### Backend

- [`normalize.py`](../app/mmt/transcripts/normalize.py): `_whisper_to_mmt` sets
  `'redactionId': None` on each word it builds and `'redactions': {}` on the
  result. Whisper input never carries redactions, and there is no lenient input
  path for them.
- `apply_mention_spans` clears and rebuilds `mentionId` and `mentions`. It must
  leave `redactionId` and `redactions` untouched, so a NER re-run does not
  discard editorial marks. This is a test, not new code — the function only
  touches the mention keys today.
- `validate_mmt_content`, `detail_json` and `update_json` need no change; the
  new fields ride along in the content.

### Frontend

[`types.ts`](../app/assets/js/transcript/types.ts):

```ts
export interface Redaction {
    mode: "remove" | "replace";
    replacement?: string | null;
    reason?: string | null;
    start?: number | null;
    end?: number | null;
}
```

with `redactionId?: string | null` on `TranscriptWord` and `redactions:
Record<string, Redaction>` on `TranscriptContent`.

[`transcript_store.ts`](../app/assets/js/transcript/transcript_store.ts) gains a
`redactions` ref and functions that mirror the mention ones one for one, all
scoped to a single segment as the mention functions are:

```ts
function redaction(redactionId?: string | null): Redaction | null
function redactionText(segmentIndex: number, redactionId?: string | null): string
function redactionRange(segmentIndex: number, redactionId: string): { start: number; end: number } | null
function createRedaction(segmentIndex: number, wordIndex: number): string
function extendRedaction(segmentIndex: number, redactionId: string, side: "left" | "right"): void
function reduceRedaction(segmentIndex: number, redactionId: string, side: "left" | "right"): void
function removeRedaction(segmentIndex: number, redactionId: string): void
function setRedactionMode(redactionId: string, mode: "remove" | "replace"): void
function setRedactionReplacement(redactionId: string, replacement: string): void
function setRedactionReason(redactionId: string, reason: string): void
function setRedactionRange(redactionId: string, start: number, end: number): void
function clearRedactionRange(redactionId: string): void
```

Behaviour pinned:

- `createRedaction` mints a `red_` id, stores `{ mode: "remove" }` and links the
  one word. The mode and any replacement are set afterwards.
- `extendRedaction` refuses to take a word that already carries a different
  `redactionId`, exactly as `extendMention` refuses to steal a word from another
  mention. It does not cross the segment boundary.
- `reduceRedaction` does nothing for a single-word redaction; `removeRedaction`
  covers that case, unlinks every word in the segment carrying the id and deletes
  the entry.
- `setRedactionMode` to `"remove"` sets `replacement` to `null`, so the content
  can never reach the backend in the state the schema rejects. Switching to
  `"replace"` leaves the replacement empty; the popover input is where the user
  fills it.
- `redactionRange` returns the redaction's own `start`/`end` when both are set,
  otherwise the first and last linked word's timestamps within the segment, and
  `null` when no word in the segment carries the id.

[`word_popover.vue`](../app/assets/js/transcript/word_popover.vue) gains a
redaction section below the mention section, built like it: when the word carries
no redaction, a heading with a single button that creates one and an empty-state
line; when it does, the same four edge buttons (extend and reduce on each side),
a remove button, the redaction's surface text as the title, and rows for the mode
select, the replacement input (rendered only in `replace` mode) and the reason
input.

[`transcript_word.vue`](../app/assets/js/transcript/transcript_word.vue) marks a
redacted word with the class `transcript-word--redacted`. The styling is a
line-through in a dedicated colour, because it has to compose with the entity
background fill and with the dirty-word underline that a word may carry at the
same time:

```css
.transcript-word--redacted {
    text-decoration: 0.125rlh line-through var(--color-redaction);
}
```

`--color-redaction: var(--pill-danger-base);` is added to
[`semantic.css`](../app/assets/css/variables/semantic.css). Unlike the entity
highlighting, redaction marking has **no display toggle**: an editorial decision
must not be invisible, so it is always rendered.

### Translations

New vue-i18n keys in both `en.js` and `de.js`:

| key | English | German |
| --- | --- | --- |
| `redaction_section` | Redaction | Anonymisierung |
| `no_redaction` | Not redacted | Nicht anonymisiert |
| `set_as_redaction` | Redact this word | Dieses Wort anonymisieren |
| `remove_redaction` | Remove redaction | Anonymisierung entfernen |
| `extend_redaction_left` | Extend to the left | Nach links erweitern |
| `extend_redaction_right` | Extend to the right | Nach rechts erweitern |
| `reduce_redaction_left` | Shorten from the left | Von links verkürzen |
| `reduce_redaction_right` | Shorten from the right | Von rechts verkürzen |
| `redaction_mode` | Mode | Modus |
| `redaction_mode_remove` | Remove | Entfernen |
| `redaction_mode_replace` | Replace | Ersetzen |
| `redaction_replacement` | Replacement | Ersatztext |
| `redaction_reason` | Reason | Grund |
| `redaction_range` | Time range | Zeitbereich |

No Django-side strings are introduced.

## Slices and tasks

Each slice leaves the system working and independently deployable.

- [ ] **1 Format extension, backend and passthrough.** Add `Redaction`,
  `RedactionId`, `Transcript.redactions` and `Word.redactionId`, extend
  `_relations`, emit the empty defaults from `_whisper_to_mmt`, and carry the
  fields through the frontend types and store without any UI. Done when
  `tests/test_mmt_schema.py` asserts that content without `redactions` still
  validates, that an unresolved `redactionId` raises, that a redaction no word
  references raises, that a redaction id colliding with a speaker, mention,
  segment or word id raises, that `replace` without a replacement and `remove`
  with one both raise, and that `start` without `end` and `start` after `end`
  raise; when `tests/test_normalize.py` asserts the empty defaults on converted
  whisper input and that `apply_mention_spans` leaves an existing redaction and
  its word links intact; and when a vitest test shows loaded content's
  `redactions` and word `redactionId` are unchanged in the payload passed to
  `updateTranscript` after a save.
- [ ] **2 Mark and unmark in the editor.** Store functions `redaction`,
  `redactionText`, `createRedaction`, `extendRedaction`, `reduceRedaction`,
  `removeRedaction`; the popover section in its create and remove states; the
  word styling, the colour variable and the locale keys. Done when
  `transcript_store.test.ts` asserts that creating mints a `red_` id with mode
  `remove` linked to the one word, that extending stops at a word already carrying
  another redaction and at the segment boundary, that reducing does nothing for a
  single-word redaction, and that removing unlinks every word and deletes the
  entry; when `word_popover.test.ts` asserts the empty state renders for an
  unmarked word and the surface text renders for a marked run; and when a
  `transcript_word` test asserts the `transcript-word--redacted` class follows the
  word's `redactionId`.
- [ ] **3 Mode, replacement and reason.** Store functions `setRedactionMode`,
  `setRedactionReplacement`, `setRedactionReason`; the mode select, the
  conditional replacement input and the reason input in the popover. Done when
  `transcript_store.test.ts` asserts that switching to `replace` and back to
  `remove` clears the replacement; when `word_popover.test.ts` asserts the
  replacement input is rendered only in `replace` mode; and when a pytest test
  posts content with a `replace` redaction to `update_json` and gets 200, and one
  with a `replace` redaction lacking a replacement gets 400.
- [ ] **4 Explicit time range.** Store functions `redactionRange`,
  `setRedactionRange`, `clearRedactionRange`; a timecode range row in the popover
  built on the existing `timecode_input.vue`, showing the derived range until the
  user overrides it and offering to clear the override. Done when
  `transcript_store.test.ts` asserts the range is derived from the first and last
  linked word, that an override wins over the derived range, and that clearing
  returns to the derived range; and when a pytest test round-trips a redaction
  with `start` and `end` through `update_json` and `detail_json`.

## Open questions

- **Redacting a region with no words** — music, background noise, a bystander
  speaking off-microphone. It is impossible in this version because a redaction
  must be referenced by at least one word. Allowing a word-free redaction means
  loosening that invariant to "referenced by a word *or* carrying an explicit
  range", which is the backward-compatible direction, plus a way to draw a range
  on the waveform. Decide when the need is real.
- **Redactions crossing segment boundaries.** The schema permits it, but every
  editor operation is scoped to one segment, as the mention operations are, so
  the editor cannot produce one. A passage-length redaction spanning many
  segments is a plausible need and would require a range selection interaction
  rather than the per-word popover.
- **Batch redaction from mentions** — "redact every `PER` mention". Cheap once
  the format exists, but it needs a review step, and it interacts with the
  entity tier once that lands (redact by entity, not by mention).
- **A redaction overview.** Once a transcript carries many redactions, finding
  and reviewing them word by word is impractical. The entity drawer from the
  entities plan is the obvious place for a second list.
