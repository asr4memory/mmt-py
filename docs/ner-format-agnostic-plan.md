# Plan: format-agnostic NER service

Status: planned (2026-07-02). Prerequisite work done: mentions map keyed by id,
`mentionId` on words, scores bounded to [0, 1], orphaned mentions rejected.

## Motivation

The NER service currently round-trips the entire mmt-transcript document: it
mirrors the transcript schema (`ner/mmt_schema.py`), must be kept in sync with
the canonical schema by hand, and could in principle drop or mangle document
fields on the way through (hence `extra="allow"` and its careful docstring).
The transcript format is the app's domain model; the NER service is a
capability — text in, entities out. After this change the service knows the
words "text", "entity", and "score", and nothing about transcripts.

What this removes:

- the mirror schema and the entire sync problem (manual resyncs, planned
  sync test, docstring drift),
- the data-integrity risk of round-tripping the document through a second
  service,
- the fuzzy string re-matching in `ner/extract.py`, including its real bugs
  (first-occurrence matching misattributes repeated words; identical entities
  in one segment collide).

Format evolution (entities tier, version bumps, renames) no longer touches the
service.

## Target contract

`POST /extract` on the NER service:

```json
// request
{"batches": [
  ["Angela", "Merkel", "besuchte", "Berlin."],
  ["Das", "war", "2019."]
]}

// response
{"results": [
  [{"start": 0, "end": 2, "label": "PER", "score": 0.93},
   {"start": 3, "end": 4, "label": "LOC", "score": 0.88}],
  [{"start": 2, "end": 3, "label": "DATE", "score": 0.91}]
]}
```

- Word-index spans, half-open `[start, end)`.
- `results` is parallel to `batches` (same length, same order).
- Spans within one batch are **non-overlapping**; the service resolves
  overlaps (highest score wins). This guarantee lives service-side because it
  is part of the boundary-rounding policy, and it means the app never has to
  decide which mention a word belongs to (a word holds a single `mentionId`).

Service internals: join each batch's words with single spaces, recording each
word's exact character range; run
`model.extract(text, schema, include_spans=True, include_confidence=True)`
(GLiNER2 returns `{"text", "start", "end", "confidence"}` per entity); map
character spans to word-index spans (any character overlap with a word claims
the whole word); resolve overlapping spans by score. All string identity stays
inside one process — only discrete word indices cross the wire.

Why word-index spans instead of the service returning character spans over
caller-supplied text: character offsets are only meaningful relative to the
exact string sent, which makes the request string load-bearing (unicode
normalization, offset units, join whitespace all silently break offsets across
a service boundary). Word indices are unambiguous, the model input is
identical either way, and the fiddly char-level alignment stays next to the
model that causes it.

## Slices

Expand → migrate → contract. Each slice leaves the system fully working and
independently deployable. Tests first throughout.

### Slice 1 — service: add `/extract` (additive; `/enrich` untouched)

- New `ner/align.py` with two pure functions:
  1. join words with offsets → `(text, [(char_start, char_end), ...])`,
  2. char-span entities + offset table → non-overlapping word-index spans.
- Tests need no model: exact alignment, punctuation attached to words
  ("Berlin."), repeated words in one batch (regression test for the current
  first-occurrence bug), mid-word span rounding, overlapping spans resolved by
  score, empty batch, span at batch end.
- `POST /extract` endpoint; request/response Pydantic models defined in
  `ner/api.py` (service-owned, no mirror). Endpoint test with mocked model.

Deployable: nothing calls the new endpoint yet.

### Slice 2 — app: switch to `/extract`; real mention scores land here

- `tasks.py`: build one batch per segment from word texts, post to
  `/extract`, merge the results.
- New merge function (e.g. `apply_mention_spans(content, results)`) replacing
  `extract_mentions`: per span, mint a `men_` id,
  `mentions[id] = {label, score}`, set `mentionId` on words `start..end`.
- Tests first: `test_extract_mentions.py` becomes
  `test_apply_mention_spans.py`; update `test_tasks.py`.
- Strict `validate_mmt_content` before persisting stays — now the only
  validation in the pipeline.
- This slice implements the pending "real NER confidences" item:
  `Mention.score` becomes real data instead of the 1.0 placeholder.

### Slice 3 — service: contract

- Delete `/enrich`, the old matching logic in `extract.py`,
  `ner/mmt_schema.py`, the old round-trip tests, and the mmt example
  fixtures.
- Adapt or retire `run_enrichment.py` (dev harness for the old flow; shrinks
  to "read words, call align/extract" if kept).
- Update the service README.

After this slice the service has zero knowledge of the transcript format.

### Slice 4 — docs and bookkeeping

- `docs/mmt-transcript-format.md` predates mentions entirely: document the
  `mentions` map, `mentionId`, and score semantics.
- Update project notes/memory: mirror gone; the planned schema sync test and
  mirror-docstring fix are cancelled (their subject matter is deleted), not
  deferred.

## Decisions folded in

- **Threshold:** keep GLiNER's default; store the raw span confidence as
  `Mention.score` unfiltered. Filtering can be a UI concern later.
- **Batching:** one HTTP request per transcript carrying all segments, as
  today (300 s timeout unchanged).
- **Multi-word entities:** one score per span from the model — maps 1:1 onto
  the mention; no aggregation.
- **Segment scope:** batches are per segment, matching today's behaviour
  (`word_group_index` was segment-scoped), so no model-context change.

## Size estimate

Slice 1 is the largest (alignment logic + its test surface), slice 2 moderate,
slices 3–4 mostly deletion and prose.
