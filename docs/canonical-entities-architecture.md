# Canonical entities architecture

Status: **draft**, written alongside
[`specs/2026-07-31-canonical-entities.md`](../specs/2026-07-31-canonical-entities.md).

This note records where the identity tier sits in the application and why it is
built the way it is. The spec records what is built; this note records the
structural decisions that outlive any single slice of it.

## Three tiers over the same words

The transcript document already carries two tiers of annotation over its words,
and this feature adds the third:

```
   identity     entities: { ent_9c2f: { name, type, aliases, wikidataId } }
                                          ^
                                          | entityId (nullable)
                                          |
  occurrence    mentions: { men_7f3a: { type, score, entityId } }
                                          ^
                                          | mentionId (nullable)
                                          |
      text      segments[].words[]: { id, start, end, word, score, ... }
```

Each tier answers a different question. The word tier answers "what was said and
when". The occurrence tier answers "which stretch of words is a name, and what
kind of name did the model think it was". The identity tier answers "which
distinct person, organisation or place is that, and what do we know about it".

Keeping them separate is what makes each of them editable on its own. Correcting
the extent of a mention does not touch the identity it points at. Renaming an
entity does not touch any mention. Re-running named-entity recognition rebuilds
the occurrence tier completely and leaves the identity tier standing, which is
the single most valuable property of the split: the work a user invested in
disambiguation survives a re-run of the model that produced the spans.

Every reference points upward and is nullable. A word may belong to no mention,
and a mention may belong to no entity. Both nulls are permanent legal states,
not unfinished work.

## Why the identity tier is in the file

Entities live in `Transcript.content` next to speakers and mentions, not in a
database table. The reason is the reason
[`mmt-transcript-format.md`](mmt-transcript-format.md) gives for deferring a
`Speaker` model: the scope of the data is one transcript, and one transcript is
one JSON document that the editor loads whole, edits whole and saves whole.

A table would buy nothing at this scope and would cost the property that makes
the editor simple: a save is one write of one document, and there is no
consistency question between a document and rows that describe it. It would also
introduce a second identity space, since the ids in the file would then have to
be reconciled with primary keys.

The trigger for a real entity table is stated in the spec and is the same as for
speakers: identity that must hold **across** transcripts, for example a person
recognised in every interview of a project. At that point the file-level register
becomes the per-transcript projection of a shared register, and the migration is
a real one. Until then, nothing in the feature assumes a database, and nothing
in the database knows about entities.

## The backend validates, the editor decides

All entity work happens in the Vue editor. The backend contributes exactly two
things:

1. **The schema and its relational invariants**, in
   `mmt/transcripts/mmt_schema.py`. Content reaching the update route is
   validated before it is stored, and the invariants say that every `entityId`
   resolves and that every entity is referenced by at least one mention.
2. **One rule pass**, in `mmt/transcripts/entity_linking.py`, called from the
   Celery task that runs named-entity recognition.

There is no entity endpoint, no partial update, no server-side entity state. The
editor holds the whole document, mutates it in memory, and posts it back. This
is the same shape speakers and mentions already have, and it is why the feature
adds no route and no migration.

The consequence for the invariants is that they are enforced twice on purpose:
the store's mutations maintain them so the editor never builds an invalid
document, and the validator enforces them so an editor bug is a rejected save
rather than corrupt stored content.

## Entities outlive their mentions

An entity without mentions is legal, and nothing removes an entity because its
last mention went away. Unlinking a mention, removing a mention and deleting the
words of a mention leave the register unchanged; only deleting an entity or
merging it into another removes it.

The register is a record the user keeps: a name, aliases and a Wikidata
identifier, entered once. Removing an entity together with its last mention
would discard that record as a side effect of an edit to the text, and the user
would have to enter it again the next time the name occurs.

The NER task is where this matters most. `apply_mention_spans` mints the whole
mentions map afresh from the service's response, so at that moment every link
is gone. The entities carried over from the source transcript stay in the
register, and the linking pass then links the new mentions whose surface text
matches one of them. An entity whose name no longer occurs stays in the
register without mentions, and is linked again when a later edit or pass
produces a matching mention.

Because nothing has to be collected, the editor's `pruneOrphans` removes only
mentions and redactions that no word references, and the validator does not
check that an entity is referenced.

## Rules only ever fill a null

Every automatic assignment in this feature, in the editor and on the backend,
writes an `entityId` only where it is `null`. None replaces a link, whoever made
it, and none creates an entity on its own.

Three properties follow, and they are the whole reason for the restriction:

- **Idempotence.** Running a pass twice changes nothing the second time, so no
  action needs to know whether it has run before.
- **Monotonicity.** A user's decision is never undone by a later automatic pass,
  so a user can run the batch actions at any point without reviewing what they
  might overwrite.
- **No provenance field.** Because a link is never overwritten, the format does
  not have to record whether a link was made by a person or by a rule. A field
  that exists only to protect manual work from automatic work is a field the
  format does not need.

The ambiguous case is decided the same way everywhere: when two entities match a
mention, nothing is linked. A rule-driven caller leaves it for the review queue,
and an interactive caller shows both and lets the user choose. Guessing between
two candidates would be the one operation that could produce a wrong link that
no later pass would correct.

## One matching rule, two implementations, one set of cases

Surface normalisation and the match rule exist in Python, for the backend pass,
and in TypeScript, for the combobox ranking and the editor's batch actions. They
are two implementations of one rule.

The alternative — a backend endpoint the editor calls for matching — was not
taken. The editor holds the whole document in memory, matching is a string
comparison over a map that is rarely larger than a few dozen entries, and a
network round trip per keystroke in a typeahead is exactly the cost the
in-memory editor exists to avoid.

What keeps two implementations honest is a single file of test cases,
`app/mmt/transcripts/tests/data/normalization_cases.json`, read by the pytest
suite and by the vitest suite. Extending the rule means adding a case,
which fails in whichever implementation has not been updated. The file lives
under the backend tree because the backend owns the format and therefore the
rule; the frontend follows it.

The rule itself is deliberately conservative: Unicode normalisation, whitespace
collapsing, edge punctuation stripping and lowercasing, and nothing else. No
stemming, no fuzzy distance, no transliteration. It exists to recognise that
"Merkel," at the end of a sentence and "Merkel" in the middle of one are the same
surface form, not to guess that "Merkel" and "Angela Merkel" are the same person.
That second judgement is what aliases are for, and aliases are entered by a
person.

Lowercasing uses `str.lower()` and `toLowerCase()` rather than Python's
`casefold()`, because `casefold()` maps `ß` to `ss` and `toLowerCase()` does
not. Agreement between the two implementations is worth more than the one
additional match that `casefold()` would produce.

## The type is stored twice and kept equal

The type of a linked mention is stored on the mention and on its entity, and the
validator requires the two to be equal. Storing it only on the entity would
make every reader of a mention, including API clients, look up the entity to
learn the type. Storing it twice keeps the mention self-contained, and the
validator's equality check keeps the two copies from diverging.

The editor maintains the equality in the store mutations that change either
side: linking a mention sets its type to the entity's type, and changing an
entity's type sets it on every linked mention. The NER model's original type
for a mention is not kept after a link changes it; the type is a decision about
an identity, and the mention follows that decision.

## Creation is usually the empty result of a search

An entity comes into existence in three ways. Two start from a mention: the
create item at the end of the combobox in the word popover, and a confirmed
suggestion built from repeated unlinked mentions. The third is the add form in
the register, which creates an entity without a mention; the linking pass and
the batch actions then link the mentions that match it.

Select-or-create as one interaction removes the decision a user would otherwise
have to make before typing: whether this name is new. The user types the name,
sees what already exists ranked by match, and either picks one or creates the
one they were about to describe. The failure mode of that interaction — creating
a duplicate that should have been a selection — is repaired by merge in two
actions, which is why merge is a slice of this feature and not a later addition.

## The drawer becomes a layout element

The register needs to be open while the user reads and edits the transcript,
which the existing drawer cannot do: it is an overlay with a backdrop, and it
covers what it annotates.

Rather than build a second component, `transcript_drawer.vue` gains `side` and
`mode`. The settings drawer keeps the defaults and does not change; the register
is a left, docked drawer that draws no backdrop and shifts the transcript
instead of covering it. On a viewport too narrow to shift anything, a docked
drawer falls back to the overlay behaviour, so there is one component with one
set of states rather than two components with a shared stylesheet.

This is also the first width media query in the project's CSS, and it is written
in `rem` rather than the `rlh` unit CLAUDE.md prescribes, because `rlh` is not
valid in a media query. That exception is confined to this one query.

## Navigation reuses what the transcript already does

Jumping from an entity to one of its mentions writes one value into the store,
`focusedMentionId`. Nothing else is pushed at the transcript.

The scrolling is done by `transcript_segment.vue`, which already scrolls itself
into view when it becomes the current segment under auto-scroll, and the
highlight is done by `transcript_word.vue`, which already styles words by their
mention. The register does not hold a reference to a DOM node in the transcript
and does not know how the transcript is laid out.

Seeking the media element goes through the media store, the same route the
transcript segments use, and it deliberately does not start playback: a jump
from the register is a reading action, not a listening one.
