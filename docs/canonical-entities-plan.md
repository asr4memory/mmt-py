# Plan: Canonical entities for mmt-transcript

Status: **draft / living document**

Adds an identity tier on top of mentions: canonical entities that multiple
mentions point to. Covers the format extension, the linking UX in the word
popover, the entity panel, and rule-based auto-assignment.

## Concept

A **mention** is one occurrence of a named entity in the transcript (exists
today). An **entity** is the identity behind mentions: canonical name, type,
optional aliases and Wikidata ID. Mentions point at entities via a nullable
`entityId` — `null` is a *legal permanent state* ("not disambiguated"), not an
unfinished TODO. Linking is decoupled from mention creation: NER and the
popover produce unlinked mentions; linking is a separate manual or rule-based
step.

### What is excluded from canonical entities

- **DATE mentions are not linkable.** "1943" or "im nächsten Sommer" has no
  identity — canonicalizing a date means *normalizing* it (to ISO 8601/EDTF),
  which is a different feature (a future `value` field on DATE mentions, out
  of scope here). Entity `type` is therefore `PER | ORG | LOC` only, and the
  popover shows the linking UI only for those labels.
- **Generic/nonspecific mentions** ("eine Stadt", "die Regierung") are handled
  by simply staying unlinked — no special mechanism needed.
- **Coreference** (pronouns, "der Zeitzeuge") is out of scope; NER doesn't
  produce such spans anyway.

### Key design decisions

- **Select-or-create is one interaction**: a typeahead combobox pre-filled
  with the mention's surface text; existing entities ranked by match, plus a
  "create '…'" item. Creating an entity is the empty-result affordance of
  searching.
- **Entities exist only through links** (created via combobox or rule pass).
  The validator mirrors the mention invariant: every `entityId` resolves,
  every entity is referenced by ≥ 1 mention, editors garbage-collect on
  unlink/merge/delete. No standalone "add entity" button initially — if a
  real need appears (preparing a register upfront), loosening the validator
  later is the backward-compatible direction.
- **Type conflict**: `mention.label` stays the raw NER claim (provenance);
  `entity.type` is authoritative for display when linked. The validator does
  *not* enforce equality; the UI warns on mismatch at link time.
- **Scope: per transcript file.** Cross-transcript identity (same person
  across interviews) is the future trigger for a real DB entity, same
  deferral logic as `Speaker`.

## Format extension

Extends version 1 **in place** — we are still in the dev phase, so no version
bump and no migration. Both new fields have defaults (`entities: {}`,
`entityId: null`), so existing v1 files validate unchanged and pick up the
fields on their next save. (Once the format is out of the dev phase, additive
changes like this become version-bump events again, as
`mmt-transcript-format.md` prescribes for `extra: forbid` schemas.)

```jsonc
{
  "format": "mmt-transcript",
  "version": 1,
  "entities": {
    "ent_9c2f": {
      "name": "Angela Merkel",       // canonical label ("name", matching Speaker; avoids clashing with mention.label)
      "type": "PER",                 // PER | ORG | LOC — no DATE
      "aliases": ["Merkel"],         // default [] — feeds rule-based linking (last-name-only is the norm in speech)
      "wikidataId": "Q567"           // optional, nullable, pattern ^Q\d+$
    }
  },
  "mentions": {
    "men_7f3a": { "label": "PER", "score": 0.93, "entityId": "ent_9c2f" }  // entityId nullable, default null
  }
}
```

Entity IDs use the existing scheme: `ent_<uuid4hex>` via `_new_id` on the
backend, the equivalent client-side for entities minted during a live edit.

## Rule-based auto-assignment

**Safety rule above all: rules only fill `entityId: null`, never overwrite an
existing link (manual or otherwise).** That makes every pass idempotent and
monotonic, and means no link-provenance field is needed in the format.

- **Normalization**: trim, casefold, collapse whitespace, strip edge
  punctuation, Unicode NFKC. Defined once here; the backend pass and the
  frontend combobox ranking implement it against shared test vectors.
- **Match rule**: normalized mention surface text equals normalized entity
  `name` *or* one of its `aliases`, **and** `mention.label == entity.type`.
  Link only when exactly **one** entity matches; ≥ 2 candidates → leave
  unlinked, surface in the review queue with the candidates listed.
- **Trigger points**:
  1. **Backend, after the NER pass** (in the flow around
     `apply_mention_spans`): run the match rule over all unlinked mentions.
     On a fresh transcript there are no entities yet, so this is a no-op — it
     becomes useful on re-runs and for transcripts with an existing register.
  2. **Frontend, on manual link**: after the user links a mention, offer
     "apply to *N* identical unlinked mentions" — explicit one-click bulk
     propagation, the main automation payoff.
  3. **Panel action "link exact matches"**: user-triggered batch run of the
     same rule, client-side.
- **Entity bootstrap (explicit, never silent)**: a panel action "suggest
  entities from repeated mentions" — cluster unlinked mentions by (normalized
  surface, label ∈ PER/ORG/LOC), propose one entity per cluster with ≥ 2
  occurrences (name = most frequent original casing), user reviews and
  confirms per cluster. This solves the cold-start problem after a first NER
  run without silent auto-creation.

## Slices

Each slice is independently deployable; tests first (pytest style backend,
vitest frontend); new UI strings go into both vue-i18n locales and, for
Django-side strings, `django.po` + `compilemessages`.

### Slice 1 — Format extension, backend + passthrough

`Entity` pydantic model, `entityId` on `Mention`, extended relational
validator (entityId resolves, no orphan entities); update `types.ts`
(`Entity`, `entityId`) and the store to load/save `entities` untouched;
update `mmt-transcript-format.md`. No UI. Deployable alone.

### Slice 2 — Manual linking in the word popover

Store: `createEntity`, `linkMention`, `unlinkMention` (with entity GC on last
unlink). Popover: "Entity" row in the mention section for PER/ORG/LOC —
unlinked: combobox (query pre-filled with surface text, ranked existing
entities + create-item, exact match preselected); linked: name, type,
Wikidata ID, unlink/change. Type-mismatch warning. This is the end-to-end
MVP: after it ships, two "Angela Merkel" mentions can point at one entity.

### Slice 3 — Entity drawer (left, docked)

`transcript_drawer.vue` grows `side: left|right` and `mode: overlay|docked`
(docked: no backdrop, content shifts, transcript stays interactive; falls
back to overlay on narrow screens); mirrored CSS variant. Entity list
following the `speaker_legend` pattern: type swatch, name, mention count,
search once the list grows; inline edit of name/type/wikidataId/aliases;
delete (= unlink all mentions, keep them as plain mentions). Absorbs the
static entity legend.

### Slice 4 — Concordance navigation

Expandable entity detail: mention list with timecode + surrounding-words
snippet; click scrolls the transcript and seeks the media (existing
seek-and-scroll machinery, entered from the panel side).

### Slice 5 — Merge

"Merge into…" in the entity detail, reusing the slice-2 combobox; repoints
all mentions, unions aliases (+ old name as alias), deletes the source. Makes
wrong create-vs-select choices a two-click repair.

### Slice 6 — Rule-based assignment

6a: backend post-NER link pass (match rule above, shared normalization test
vectors). 6b: "apply to N identical unlinked mentions" after a manual link.
6c: panel review queue — unlinked count on top, walk mention by mention with
suggested candidates (accept / pick / create / skip), plus "link exact
matches" and "suggest entities from repeated mentions" batch actions.

### Slice 7 (deferred) — Wikidata lookup

Candidate search against the Wikidata API in the entity edit form (prefill
name/aliases from labels). The `wikidataId` field exists from slice 1, so
this is purely additive UI; needs a decision on client-side vs.
backend-proxied requests.

## Open questions

- Merge alias policy: always keep the losing entity's name as an alias, or
  ask?
- Should the review queue (6c) live in the drawer or as a mode of the
  transcript view (highlighting the current unlinked mention in place)?
- When date normalization eventually lands: separate `value` field on DATE
  mentions vs. a parallel structure — decide then.
