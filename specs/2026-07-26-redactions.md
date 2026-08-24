# Redacted sections in the mmt-transcript format

Executable spec: the decisions for recording redacted passages in the
mmt-transcript content and the editor operations that create and edit them.

## Motivation

Interviews contain names and passages that must not be published. That editorial
decision is made once in the editor and has to persist with the transcript so
every later export can apply it. Redactions reuse the shape of the mentions map,
and a word may carry both ids at once.

## Non-goals

- **No application.** The rule is pinned below; producing silenced media or a
  redacted export is separate work.
- **No access control.** The unredacted words stay in `Transcript.content`.
- **No replacement text.** Pseudonyms belong on the entity, designed in
  [`docs/canonical-entities-plan.md`](../docs/canonical-entities-plan.md).
- **No time-anchored redactions.** `start` and `end` are in the schema but
  nothing writes them.
- **No automatic redaction and no overview UI.**
- **No schema version bump.** The fields are additive with defaults.

## Feature reference

A **redaction** is one contiguous run of words that must not be published, plus
an optional reason. The words fix which text it affects, the range derived from
them which audio.

### Schema

In [`mmt_schema.py`](../app/mmt/transcripts/mmt_schema.py):

```python
RedactionId = Annotated[str, StringConstraints(min_length=1)]


class Redaction(BaseModel):
    model_config = ConfigDict(extra='forbid')

    reason: str | None = None
    start: float | None = Field(default=None, ge=0)
    end: float | None = Field(default=None, ge=0)

    @model_validator(mode='after')
    def _consistent(self):
        if (self.start is None) != (self.end is None):
            raise ValueError('redaction needs both start and end or neither')
        if self.start is not None and self.start > self.end:
            raise ValueError('redaction: start after end')
        return self
```

`Word` gains `redactionId: str | None = None`; `Transcript` gains
`redactions: dict[RedactionId, Redaction] = {}`.

`_relations` mirrors the mention invariants: ids claimed into `seen_ids`, every
`redactionId` resolves, every redaction referenced by at least one word, with the
messages `word {id}: unknown redactionId {value!r}` and `orphaned redaction
{id!r}: no word references it`. Contiguity is not enforced, and nothing
constrains `mentionId` against `redactionId`.

### Applying a redaction

> Applying a redaction masks both the text and the media. In the text, each
> linked word's `word` becomes the marker `XXX`, keeping its `id`, `start`,
> `end` and `speakerId`, and clearing its `mentionId` and `redactionId`. In the
> media, the effective range is silenced.

One marker per word, so no segment loses all its words. The marker is an export
constant, not stored, and masking both channels is the retroactive meaning of
everything stored under this version.

### The time range

The effective range is the first word's `start` and the last word's `end`;
padding is an export decision, not stored. `start` and `end` are inert here,
validated and carried but written by nothing, and override the derived range when
set. A region containing no words cannot be redacted.

### IDs

Prefix `red`: `_new_id('red')` on the backend, `newId("red")` in the store.

### Backend

`_whisper_to_mmt` in [`normalize.py`](../app/mmt/transcripts/normalize.py) sets
`'redactionId': None` per word and `'redactions': {}` on the result.
`apply_mention_spans` must leave both untouched, so a NER re-run does not discard
editorial marks; that is a test, not new code. `validate_mmt_content`,
`detail_json` and `update_json` need no change.

### Frontend

[`types.ts`](../app/assets/js/transcript/types.ts): a `Redaction` interface with
`reason`, `start` and `end` optional and nullable, `redactionId?: string | null`
on `TranscriptWord`, `redactions: Record<string, Redaction>` on
`TranscriptContent`.

[`transcript_store.ts`](../app/assets/js/transcript/transcript_store.ts) gains a
`redactions` ref and functions mirroring the mention ones, all segment-scoped:

```ts
function redaction(redactionId?: string | null): Redaction | null
function redactionText(segmentIndex: number, redactionId?: string | null): string
function createRedaction(segmentIndex: number, wordIndex: number): string
function extendRedaction(segmentIndex: number, redactionId: string, side: "left" | "right"): void
function reduceRedaction(segmentIndex: number, redactionId: string, side: "left" | "right"): void
function removeRedaction(segmentIndex: number, redactionId: string): void
function setRedactionReason(redactionId: string, reason: string): void
```

`extendRedaction` refuses a word carrying a different `redactionId`,
`reduceRedaction` does nothing for a single-word redaction, and nothing writes
`start` or `end`.

[`word_popover.vue`](../app/assets/js/transcript/word_popover.vue) gains a
redaction section below the mention section, built like it: an empty state with a
create button, or the four edge buttons, a remove button, the surface text as
title and a reason input.

[`transcript_word.vue`](../app/assets/js/transcript/transcript_word.vue) marks a
redacted word `transcript-word--redacted`, a line-through so it composes with the
entity fill and the dirty-word underline, with a new `--color-redaction:
var(--pill-danger-base);` in
[`semantic.css`](../app/assets/css/variables/semantic.css):

```css
.transcript-word--redacted {
    text-decoration: 0.125rlh line-through var(--color-redaction);
}
```

There is no display toggle: an editorial decision must not be invisible.

### Translations

New vue-i18n keys in both `en.js` and `de.js`. No Django-side strings.

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
| `redaction_reason` | Reason | Grund |

## Slices and tasks

- [ ] **1 Format extension, backend and passthrough.** Schema, invariants,
  `_whisper_to_mmt` defaults, frontend types and store passthrough, no UI. Done
  when `test_mmt_schema.py` covers content without `redactions`, an unresolved
  `redactionId`, an unreferenced redaction, an id colliding with a speaker,
  mention, segment or word, `start` without `end` and `start` after `end`; when
  `test_normalize.py` covers the empty defaults and `apply_mention_spans` leaving
  a redaction intact; when a pytest test round-trips reason, `start` and `end`
  through `update_json` and `detail_json`; and when a vitest test shows both
  fields unchanged in the `updateTranscript` payload.
- [ ] **2 Mark and unmark in the editor.** Store functions, popover section, word
  styling, colour variable, locale keys. Done when `transcript_store.test.ts`
  covers creating, extending into another redaction and past the segment
  boundary, reducing a single-word redaction, removing, and setting a reason
  without touching `start` or `end`; and when `word_popover.test.ts` and a
  `transcript_word` test cover the empty and marked states and the class
  following `redactionId`.

## Open questions

- **Time-anchored redactions**, for music, noise or a bystander off-microphone:
  one map and one id space, the invariant loosened to "referenced by a word **or**
  carrying both `start` and `end`", and a range drawn on the waveform linking
  every word it overlaps. Missing is that range-selection interaction, which is
  also what would create a redaction crossing segments.
- **Per-channel masking**: separate booleans for audio and video rather than an
  enum, defaulting to agree with the application rule. Blurring a region of the
  frame is a different feature needing a spatial box over time.
- **Batch redaction from mentions**, which needs a review step and interacts with
  the entity tier.
- **A redaction overview**, for which the entity drawer is the obvious place.
