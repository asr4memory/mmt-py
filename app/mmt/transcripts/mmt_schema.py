from typing import Annotated, Literal

from django.core.exceptions import ValidationError as DjangoValidationError
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

MentionId = Annotated[str, StringConstraints(min_length=1)]
EntityId = Annotated[str, StringConstraints(min_length=1)]
RedactionId = Annotated[str, StringConstraints(min_length=1)]
Alias = Annotated[str, StringConstraints(min_length=1)]


class Speaker(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: str = Field(min_length=1)
    name: str
    color: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')


class Entity(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = Field(min_length=1)
    # DATE is deliberately absent: a date has no identity, so no entity
    # carries that type and a DATE mention is never linked.
    type: Literal['PER', 'ORG', 'LOC']
    aliases: list[Alias] = []
    # The pattern rejects Q0 and leading zeros, which are not Wikidata
    # identifiers, and is anchored so a whole label ('Q567 (Angela Merkel)')
    # is rejected rather than partly accepted.
    wikidataId: str | None = Field(default=None, pattern=r'^Q[1-9][0-9]*$')


class Mention(BaseModel):
    model_config = ConfigDict(extra='forbid')

    label: Literal['PER', 'ORG', 'DATE', 'LOC']
    score: float = Field(default=1.0, ge=0, le=1)
    # None is a legal permanent state, not an unfinished one: a mention that
    # nobody has linked to an identity.
    entityId: str | None = None


class Redaction(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # Free text recording why the passage must not be published. An empty
    # string is legal; the field exists for the user, not for the format.
    reason: str | None = None
    # Inert in this version: validated and carried through, but nothing
    # writes them. When set they override the range derived from the words.
    start: float | None = Field(default=None, ge=0)
    end: float | None = Field(default=None, ge=0)

    @model_validator(mode='after')
    def _consistent(self):
        if (self.start is None) != (self.end is None):
            raise ValueError('redaction needs both start and end or neither')
        if self.start is not None and self.start > self.end:
            raise ValueError('redaction: start after end')
        return self


class Word(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    word: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)
    speakerId: str | None = None
    mentionId: str | None = None
    # Independent of mentionId: a word may carry both, one or neither.
    redactionId: str | None = None

    @model_validator(mode='after')
    def _ordered(self):
        if self.start > self.end:
            raise ValueError(f'word {self.id}: start after end')
        return self


class Segment(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    speakerId: str | None = None
    words: list[Word] = Field(min_length=1)

    @model_validator(mode='after')
    def _ordered(self):
        if self.start > self.end:
            raise ValueError(f'segment {self.id}: start after end')
        return self


class Transcript(BaseModel):
    model_config = ConfigDict(extra='forbid')

    format: Literal['mmt-transcript']
    version: Literal[1]
    # ISO 639-1 code; None when unknown. Optional with a None default, so
    # content stored before the field existed still validates within version 1.
    language: str | None = None
    speakers: list[Speaker]
    entities: dict[EntityId, Entity]
    mentions: dict[MentionId, Mention] = {}
    redactions: dict[RedactionId, Redaction]
    segments: list[Segment] = Field(min_length=1)

    @model_validator(mode='after')
    def _relations(self):
        """Invariants the per-field types cannot express: id uniqueness across
        every speaker/entity/mention/redaction/segment/word, that each
        speakerId, mentionId, entityId and redactionId resolves, and that
        every mention is referenced by at least one word, every entity by at
        least one mention and every redaction by at least one word (editors
        must garbage-collect orphaned entries before saving). Redactions carry
        two further invariants the other tiers do not: the words of one
        redaction lie in a single segment and occupy consecutive positions in
        it, because the time range a redaction silences is derived from its
        first and last word."""
        speaker_ids = {speaker.id for speaker in self.speakers}
        seen_ids = set()
        referenced_mention_ids = set()
        referenced_entity_ids = set()
        # Per redaction id: the id of the segment it was first seen in, the
        # positions it occupies in that segment's word list, and whether it
        # was seen in a second segment.
        redaction_segment_ids = {}
        redaction_positions = {}
        split_redaction_ids = set()

        def claim(obj_id, kind):
            if obj_id in seen_ids:
                raise ValueError(f'duplicate id {obj_id!r} ({kind})')
            seen_ids.add(obj_id)

        def check_speaker_ref(speaker_id, obj_id, kind):
            if speaker_id is not None and speaker_id not in speaker_ids:
                raise ValueError(f'{kind} {obj_id}: unknown speakerId {speaker_id!r}')

        for speaker in self.speakers:
            claim(speaker.id, 'speaker')

        for entity_id in self.entities:
            claim(entity_id, 'entity')

        for mention_id, mention in self.mentions.items():
            claim(mention_id, 'mention')
            if mention.entityId is not None:
                if mention.entityId not in self.entities:
                    raise ValueError(
                        f'mention {mention_id}: unknown entityId {mention.entityId!r}'
                    )
                referenced_entity_ids.add(mention.entityId)

        for redaction_id in self.redactions:
            claim(redaction_id, 'redaction')

        for segment in self.segments:
            claim(segment.id, 'segment')
            check_speaker_ref(segment.speakerId, segment.id, 'segment')
            for position, word in enumerate(segment.words):
                claim(word.id, 'word')
                check_speaker_ref(word.speakerId, word.id, 'word')
                if word.mentionId is not None:
                    if word.mentionId not in self.mentions:
                        raise ValueError(
                            f'word {word.id}: unknown mentionId {word.mentionId!r}'
                        )
                    referenced_mention_ids.add(word.mentionId)
                if word.redactionId is not None:
                    if word.redactionId not in self.redactions:
                        raise ValueError(
                            f'word {word.id}: unknown redactionId {word.redactionId!r}'
                        )
                    if word.redactionId not in redaction_segment_ids:
                        redaction_segment_ids[word.redactionId] = segment.id
                        redaction_positions[word.redactionId] = []
                    if redaction_segment_ids[word.redactionId] != segment.id:
                        split_redaction_ids.add(word.redactionId)
                    else:
                        redaction_positions[word.redactionId].append(position)

        for mention_id in self.mentions.keys() - referenced_mention_ids:
            raise ValueError(f'orphaned mention {mention_id!r}: no word references it')

        for entity_id in self.entities.keys() - referenced_entity_ids:
            raise ValueError(f'orphaned entity {entity_id!r}: no mention references it')

        for redaction_id in self.redactions.keys() - redaction_positions.keys():
            raise ValueError(
                f'orphaned redaction {redaction_id!r}: no word references it'
            )

        # Spanning segments is checked before contiguity, so a redaction that
        # violates both is reported as the more specific fault.
        for redaction_id in split_redaction_ids:
            raise ValueError(
                f'redaction {redaction_id!r}: words lie in more than one segment'
            )

        for redaction_id, positions in redaction_positions.items():
            # The positions within one segment are distinct by construction,
            # so this comparison is an exact contiguity test.
            if max(positions) - min(positions) + 1 != len(positions):
                raise ValueError(
                    f'redaction {redaction_id!r}: words are not contiguous'
                )

        return self


def validate_mmt_content(content) -> Transcript:
    """Strictly validate our own mmt-transcript format (version 1).

    Structure, types, enums, the colour format, and the relational invariants
    are all expressed on the Pydantic models above. This guards data the
    backend itself produced, so a failure is a bug rather than user input.
    Returns the parsed Transcript; re-raises Pydantic's error as Django's
    ValidationError so it plugs into model.clean()/form validation.
    """
    try:
        return Transcript.model_validate(content)
    except ValidationError as error:
        raise DjangoValidationError(
            [
                f'{".".join(str(part) for part in item["loc"])}: {item["msg"]}'
                for item in error.errors()
            ]
        )
