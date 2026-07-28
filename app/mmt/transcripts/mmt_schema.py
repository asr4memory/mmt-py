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


class Speaker(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: str = Field(min_length=1)
    name: str
    color: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')


class Mention(BaseModel):
    model_config = ConfigDict(extra='forbid')

    label: Literal['PER', 'ORG', 'DATE', 'LOC']
    score: float = Field(default=1.0, ge=0, le=1)


class Word(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    word: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)
    speakerId: str | None = None
    mentionId: str | None = None

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
    mentions: dict[MentionId, Mention] = {}
    segments: list[Segment] = Field(min_length=1)

    @model_validator(mode='after')
    def _relations(self):
        """Invariants the per-field types cannot express: id uniqueness across
        every speaker/mention/segment/word, that each speakerId and mentionId
        resolves, and that every mention is referenced by at least one word
        (editors must garbage-collect orphaned mentions before saving)."""
        speaker_ids = {speaker.id for speaker in self.speakers}
        seen_ids = set()
        referenced_mention_ids = set()

        def claim(obj_id, kind):
            if obj_id in seen_ids:
                raise ValueError(f'duplicate id {obj_id!r} ({kind})')
            seen_ids.add(obj_id)

        def check_speaker_ref(speaker_id, obj_id, kind):
            if speaker_id is not None and speaker_id not in speaker_ids:
                raise ValueError(f'{kind} {obj_id}: unknown speakerId {speaker_id!r}')

        for speaker in self.speakers:
            claim(speaker.id, 'speaker')

        for mention_id in self.mentions:
            claim(mention_id, 'mention')

        for segment in self.segments:
            claim(segment.id, 'segment')
            check_speaker_ref(segment.speakerId, segment.id, 'segment')
            for word in segment.words:
                claim(word.id, 'word')
                check_speaker_ref(word.speakerId, word.id, 'word')
                if word.mentionId is not None:
                    if word.mentionId not in self.mentions:
                        raise ValueError(
                            f'word {word.id}: unknown mentionId {word.mentionId!r}'
                        )
                    referenced_mention_ids.add(word.mentionId)

        for mention_id in self.mentions.keys() - referenced_mention_ids:
            raise ValueError(f'orphaned mention {mention_id!r}: no word references it')

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
