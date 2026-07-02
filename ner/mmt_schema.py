"""mmt-transcript Pydantic models for the NER service.

Duplicated from ``app/mmt/transcripts/mmt_schema.py`` (the canonical source).
We can't import that module here because it pulls in Django (it raises
``django.core.exceptions.ValidationError``), and this service is a standalone
deployable with no Django dependency. Keep the two in sync — same pattern as
``SPEAKER_COLORS`` mirrored in ``app/mmt/transcripts/normalize.py``.

Difference from the app copy: ``extra="allow"`` everywhere so the service stays
lenient toward legacy/dev fields and never silently drops data on the request or
the ``response_model``. Two kinds of undeclared field ride through this way: the
whisperX ``score_log``, and the service's own flat NER signal (``ner_entity``
and ``word_group_index``) that ``enrich_transcript`` attaches to tagged words.
The app then materialises that signal into the canonical ``mentions`` map (words
point at a mention via ``mentionId``) and runs the strict relational
validation — both stay on the app side.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MentionId = Annotated[str, StringConstraints(min_length=1)]


class Speaker(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    name: str
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


class Mention(BaseModel):
    model_config = ConfigDict(extra="allow")

    label: Literal["PER", "ORG", "DATE", "LOC"]
    score: float = Field(default=1.0, ge=0, le=1)


class Word(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    word: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)
    speakerId: str | None = None
    mentionId: str | None = None


class Segment(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str
    speakerId: str | None = None
    words: list[Word] = Field(min_length=1)


class Transcript(BaseModel):
    model_config = ConfigDict(extra="allow")

    format: Literal["mmt-transcript"]
    version: Literal[1]
    speakers: list[Speaker]
    mentions: dict[MentionId, Mention] = {}
    segments: list[Segment] = Field(min_length=1)
