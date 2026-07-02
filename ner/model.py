from gliner2 import GLiNER2

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
