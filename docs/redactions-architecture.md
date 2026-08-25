# Redactions architecture

Status: **draft**, written alongside
[`specs/2026-07-26-redactions.md`](../specs/2026-07-26-redactions.md).

This note records where redactions sit in the application and why they are built
the way they are. The spec records what is built; this note records the
structural decisions that outlive any single slice of it.

## A second occurrence tier over the same words

The transcript document carries an annotation stack over its words, described in
[`canonical-entities-architecture.md`](canonical-entities-architecture.md).
Redactions add a tier beside the occurrence tier rather than above or below it:

```
   identity     entities:   { ent_9c2f: { name, type, aliases, wikidataId } }
                                     ^
                                     | entityId (nullable)
                                     |
  occurrence    mentions:   { men_7f3a: { label, score, entityId } }      redactions: { red_4b1e: { reason, start, end } }
                                     ^                                                       ^
                                     | mentionId (nullable)                                  | redactionId (nullable)
                                     |                                                       |
      text      segments[].words[]:  { id, start, end, word, score, speakerId, mentionId, redactionId }
```

The two occurrence tiers answer different questions about the same stretch of
words. The mention tier answers "which stretch of words is a name, and what kind
of name did the model think it was". The redaction tier answers "which stretch
of words must not be published, and why". Neither is derived from the other.

They are deliberately unconstrained against each other. A word may carry a
`mentionId`, a `redactionId`, both or neither; a redaction may cover part of a
mention, all of it, or several mentions at once. The common case is redacting a
name that the named-entity pass already marked as a `PER` mention, which is
exactly the case a constraint between the two would make awkward. The other
frequent case, a whole passage covering many words of which only some are names,
has no relation to the mention tier at all.

The independence has one operational consequence that is worth stating on its
own: re-running named-entity recognition rebuilds the mention tier completely
and must leave the redaction tier standing. `apply_mention_spans` touches the
mention keys only, so this holds today by construction, and the spec pins it as
a test so that it keeps holding.

## A redaction is a mark, not an edit

Marking a passage as redacted changes nothing about the words. The word text,
its timestamps, its identifier and its speaker are all untouched, and
`Transcript.content` continues to hold what was said.

The alternative — editing the words in place when the editorial decision is made
— was not taken, for three reasons. The decision would not be reversible, since
the original wording would be gone. The decision would not be reviewable, since
nothing would distinguish a passage that was redacted from a passage that was
transcribed that way. And the decision could not be applied differently in
different places, which is the point of recording it at all: the same transcript
is the source of a published subtitle file, an archived master and a copy shared
inside a research group, and those need not be redacted alike.

What follows from this is that a redaction is only ever meaningful together with
something that applies it. Recording the mark and applying it are separate work,
and the format is designed so that the second can be built later without another
schema change.

## The meaning is pinned before the application is built

Nothing in the application applies a redaction yet. The rule for what applying
one means is nevertheless part of this feature and not of the later export work,
because a mark that is stored before its meaning is fixed is a mark whose
meaning can only be guessed later.

The rule is that applying a redaction masks both channels: in the text each
linked word becomes a fixed marker, and in the media the effective time range is
silenced. This is the retroactive meaning of every redaction stored under this
version of the format. An export that wants to mask only one of the two channels
is a change of meaning and needs a field that says so, which the open questions
in the spec sketch and this version does not have.

## One marker per word

Applying a redaction to the text replaces each linked word's `word` value with
one marker, rather than replacing the whole run with one string.

This keeps the mapping between the stored document and the applied document one
to one. Every word keeps its identifier, its timestamps and its speaker, so a
redacted document still aligns with the media, still produces word-level
timings, and still satisfies the schema's requirement that a segment holds at
least one word. A run-level replacement would have to invent a timestamp for the
replacement, decide which of the original words it inherits its identifier from,
and handle the case where the run is a whole segment.

This is also why the earlier design's `replace` mode was dropped. Substituting a
passage with free replacement text had no defined mapping from a multi-word
replacement onto the words it replaces and their timestamps, and every candidate
rule for that mapping was arbitrary.

## Pseudonyms belong to the identity tier

A pseudonym is a property of a person, not of one occurrence of their name. "Mr
A" has to be the same "Mr A" in all forty places the interview names him, and
that consistency is exactly what the identity tier exists to express.

Storing replacement text on a redaction would put it one tier too low: forty
redactions would each carry their own copy of the pseudonym, and nothing would
keep the copies equal. Once pseudonyms are built they belong on `Entity`, next
to the canonical name and the aliases, and a redaction says only that the
passage must not be published.

## Redactions reuse the mention shape, invariants included

A redaction is one entry in a transcript-level map, and the words that belong to
it point at it by identifier. That is the shape the mentions map already has,
and reusing it means reusing everything already built around it: the identifier
scheme with a three-letter prefix, the single namespace that keeps identifiers
unique across speakers, entities, mentions, segments and words, the relational
checks in `Transcript._relations`, and the rule that an entry no word references
is invalid rather than merely useless.

That last rule is what makes removing a redaction a complete operation: the
editor unlinks the words and deletes the entry together, and a document that
reaches the validator with a redaction nothing points at is a bug in the editor
rather than an accepted state. It is the same garbage collection the editor
already performs for mentions and entities.

The one thing not reused is a per-tier constraint that mentions do not have
either: the words of a redaction are not checked for contiguity. The editor only
ever produces contiguous runs, because every operation works from the ends of
the existing run, but the validator does not enforce it, for the same reason it
does not enforce it for mentions — a run that has been split by an edit
elsewhere is a display question, not a corrupt document.

## The words anchor the text, the range follows from them

A redaction is anchored to words rather than to a time range, because the
editorial decision is made while reading and is about text. The audio range
follows from the words: the first word's start and the last word's end.

The schema nevertheless carries `start` and `end` on a redaction, validated and
carried through but written by nothing in this version. They are there because
the case they serve is real and known — music, background noise, a bystander
speaking off-microphone, or the audio between two words that no word's range
covers — and because adding them now costs one validator and no migration,
while adding them later would mean a second pass over stored documents.

Making them inert rather than editable is the decision that keeps this version
small. An explicit range needs a way to draw one on the waveform, and that
interaction is the same one that a redaction crossing segment boundaries would
need. Both are recorded as open questions in the spec rather than built.

## The backend validates, the editor decides

Every redaction is created, edited and removed in the Vue editor, in memory,
against the whole document the editor already holds. The backend contributes the
schema and its relational invariants, and nothing else: no redaction endpoint,
no partial update, no server-side redaction state.

This is the shape speakers, mentions and entities already have, and it is why
the feature adds no route and no migration. The invariants are consequently
enforced twice on purpose — the store's mutations maintain them so the editor
never builds an invalid document, and the validator enforces them so an editor
bug is a rejected save rather than corrupt stored content.

## Marking is always visible

Entity highlighting in the transcript can be switched off; redaction marking
cannot. `transcript_word.vue` takes a `showEntities` prop and there is no
equivalent for redactions.

The asymmetry is intentional. Entity highlighting is a reading aid, and a reader
who does not want it loses nothing by hiding it. A redaction is an editorial
decision with consequences outside the application, and a user who cannot see
that a passage is marked can neither review the decision nor notice that it was
made by mistake. Hiding it would also make the two states of the word popover
unreachable in a predictable way.

The visual treatment is a line-through in a dedicated colour rather than a
background fill, because a redacted word may at the same time carry an entity
fill and the dirty-word underline. Three simultaneous states over one word need
three channels that do not overwrite each other.

## Redaction is not access control

A redacted transcript is not a restricted transcript. The words stay in
`Transcript.content`, the editor shows them, the existing JSON download serves
them, and every user who may open the transcript reads exactly what was said.

Access control is a different question, answered by the ownership check every
transcript route already performs. Conflating the two would give a false
guarantee: a mark that looks like protection but is applied by whichever export
happens to read it. What a redaction guarantees is narrower and honest — that
the decision travels with the transcript, so that any export which applies
redactions applies all of them.
