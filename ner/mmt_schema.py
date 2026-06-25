"""mmt-transcript Pydantic models for the NER service.

Duplicated from ``app/mmt/transcripts/mmt_schema.py`` (the canonical source).
We can't import that module here because it pulls in Django (it raises
``django.core.exceptions.ValidationError``), and this service is a standalone
deployable with no Django dependency. Keep the two in sync — same pattern as
``SPEAKER_COLORS`` mirrored in ``app/mmt/transcripts/normalize.py``.

Difference from the app copy: ``extra="allow"`` everywhere so the service stays
lenient toward legacy/dev fields (e.g. whisperX ``score_log``) and never
silently drops data on the request or the ``response_model``. Strict relational
validation stays on the app side (``validate_mmt_content`` in ``tasks.py``).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Speaker(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    name: str
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


class Word(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    word: str = Field(min_length=1)
    score: float
    speakerId: str | None = None
    ner_entity: str | None = None
    word_group_index: int | None = None


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
    segments: list[Segment] = Field(min_length=1)
