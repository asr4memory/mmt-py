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
   identity     entities: { ent_9c2f: { name, type, wikidataId } }
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

All entity work happens in the Vue editor. The backend contributes exactly one
thing: **the schema and its relational invariants**, in
`mmt/transcripts/mmt_schema.py`. Content reaching the update route is validated
before it is stored, and the invariants say that every `entityId` resolves,
that a linked mention has the type of its entity, and that no two entities
share a name or a Wikidata identifier.

There is no entity endpoint, no partial update, no server-side entity state. The
editor holds the whole document, mutates it in memory, and posts it back. This
is the same shape speakers and mentions already have, and it is why the feature
adds no route.

The consequence for the invariants is that they are enforced twice on purpose:
the store's mutations maintain them so the editor never builds an invalid
document, and the validator enforces them so an editor bug is a rejected save
rather than corrupt stored content.

## Entities outlive their mentions

An entity without mentions is legal, and nothing removes an entity because its
last mention went away. Unlinking a mention, removing a mention and deleting the
words of a mention leave the register unchanged; only deleting an entity
removes it.

The register is a record the user keeps: a name and a Wikidata identifier,
entered once. Removing an entity together with its last mention
would discard that record as a side effect of an edit to the text, and the user
would have to enter it again the next time the name occurs.

The NER task is where this matters most. `apply_mention_spans` mints the whole
mentions map afresh from the service's response, so at that moment every link
is gone. The entities carried over from the source transcript stay in the
register without mentions, and the user links the new mentions to them again.

Because nothing has to be collected, the editor's `pruneOrphans` removes only
mentions and redactions that no word references, and the validator does not
check that an entity is referenced.

## Every link is set by the user

No rule, pass or batch action assigns an `entityId`, and none creates an entity
on its own. A link exists because a user confirmed an entity for a mention.

Because every link has the same origin, the format does not have to record
whether a link was made by a person or by a rule. A field that exists only to
protect manual work from automatic work is a field the format does not need.

## Names are compared exactly

An entity has one name and no aliases. No two entities in the register share a
name, whatever their type, and the comparison is an exact string comparison:
names that differ in case, whitespace or punctuation are different names. There
is no normalisation of names and therefore no second implementation of a
normalisation rule to keep in agreement between the backend and the editor.

The editor trims a name before storing it. The only other text processing is
the prefill of the name input in the combobox, which removes whitespace,
punctuation and symbols from both edges of the mention's surface text, so that
"Merkel," at the end of a sentence is proposed as `Merkel`.

## The type is stored twice and kept equal

The type of a linked mention is stored on the mention and on its entity, and the
validator requires the two to be equal. Storing it only on the entity would
make every reader of a mention, including API clients, look up the entity to
learn the type. Storing it twice keeps the mention self-contained, and the
validator's equality check keeps the two copies from diverging.

The editor maintains the equality when it links a mention: the mention's type
is set to the entity's type. An entity's type is set when the entity is created
and cannot be changed, so no other edit can break the equality. The NER model's
original type
for a mention is not kept after a link changes it; the type is a decision about
an identity, and the mention follows that decision.

## Selecting and creating are separate actions

An entity comes into existence in two ways: the create action in the
combobox of the word popover, which creates an entity from a mention and links
the mention to it, and the add form in the register, which creates an entity
without a mention.

The combobox offers two separate actions: choosing an existing entity in a
select, sorted by name, or creating a new entity from a name typed into an
input. There is no ranking of the entities and no preselection. A duplicate
created by mistake is repaired by linking its mentions to the other entity and
deleting it.

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

Jumping from an entity to one of its mentions scrolls the transcript to the
mention's segment. The register emits the segment's index, and the transcript
table scrolls that segment into view through the same lookup that the jump to
the current playback segment uses. The register does not hold a reference to a
DOM node in the transcript and does not know how the transcript is laid out.

A jump is a reading action: it does not move the playback position and does not
change any content.
