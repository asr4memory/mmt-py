from fastapi import FastAPI

from extract import enrich_transcript
from mmt_schema import Transcript

app = FastAPI()


@app.post("/enrich", response_model_exclude_none=True)
def enrich(transcript: Transcript) -> Transcript:
    result = enrich_transcript(transcript.model_dump(exclude_none=True))
    return Transcript.model_validate(result)
