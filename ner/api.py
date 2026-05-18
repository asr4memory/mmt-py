from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from extract import enrich_transcript

app = FastAPI()


class Word(BaseModel):
    model_config = ConfigDict(extra="allow")

    word: str
    start: float
    end: float
    score: float | None = None
    score_log: float | None = None
    speaker: str | None = None
    ner_entity: str | None = None
    word_group_index: int | None = None


class Segment(BaseModel):
    model_config = ConfigDict(extra="allow")

    start: float
    end: float
    text: str
    speaker: str | None = None
    words: list[Word]


class Transcript(BaseModel):
    segments: list[Segment]


@app.post("/enrich", response_model_exclude_none=True)
def enrich(transcript: Transcript) -> Transcript:
    result = enrich_transcript(transcript.model_dump(exclude_none=True))
    return Transcript.model_validate(result)
