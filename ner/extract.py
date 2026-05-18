import string

from gliner2 import GLiNER2
from rapidfuzz import fuzz

MODEL_NAME = "fastino/gliner2-multi-v1"

ENTITY_LABELS = {
    "PER": "Named persons (real or fictional), including full names, last names with clear reference, titles with names, pseudonyms, and clearly identifiable named person groups",
    "LOC": "Geographical or physical locations such as countries, cities, regions, natural features, buildings, landmarks, and full postal addresses",
    "ORG": "Organizations and institutions including companies, government bodies, political parties, NGOs, educational institutions, sports teams, bands, and other formal groups acting as entities",
    "DATE": "Concrete dates and time references including full dates, years, date ranges, centuries, relative dates (e.g. today, last year), and named calendar events",
}

_model = None
_schema = None


def get_model():
    global _model, _schema
    if _model is None:
        _model = GLiNER2.from_pretrained(MODEL_NAME)
        _schema = _model.create_schema().entities(ENTITY_LABELS)
    return _model, _schema


def enrich_transcript(transcript: dict) -> dict:
    model, schema = get_model()

    for entry in transcript["segments"]:
        groupindex = 0
        text = entry["text"]
        gliner_results = model.extract(text, schema)

        result_tuple = []
        for entity_type in gliner_results["entities"]:
            for word in gliner_results["entities"][entity_type]:
                result_tuple.append((word, entity_type))

        if not result_tuple:
            continue

        for words in entry["words"]:
            original_word = words["word"].translate(str.maketrans("", "", string.punctuation))
            for ner_tuple in result_tuple:
                if original_word == ner_tuple[0]:
                    if "ner_entity" not in words:
                        words["ner_entity"] = ner_tuple[1]

                elif original_word in ner_tuple[0] and len(ner_tuple[0].split(" ")) > 1:
                    first_part = ner_tuple[0].split(" ")[0]
                    if fuzz.ratio(original_word, first_part) > 90:
                        index = next(
                            (i for i, item in enumerate(entry["words"]) if item["word"] == original_word),
                            -1,
                        )
                        for _, part in enumerate(ner_tuple[0].split(" ")):
                            word_clean = entry["words"][index]["word"].translate(
                                str.maketrans("", "", string.punctuation)
                            )
                            if word_clean == part and "ner_entity" not in entry["words"][index]:
                                entry["words"][index]["ner_entity"] = ner_tuple[1]
                                entry["words"][index]["word_group_index"] = groupindex
                            index += 1
                        groupindex += 1

    return transcript
