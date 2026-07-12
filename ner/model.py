from gliner2 import GLiNER2

MODEL_NAME = "fastino/gliner2-multi-v1"

ENTITY_LABELS = {
    "PER": "The proper name of a person, such as Angela Merkel, Merkel, or Dr. Angela Merkel",
    "LOC": "The proper name of a place, such as Germany, Berlin, the Rhine, or the Brandenburg Gate",
    "ORG": "The proper name of an organization, such as Siemens, NASA, the Red Cross, or the United Nations",
    "DATE": "A date or time reference, such as 3 March 2019, 2019, the 1990s, last August, today, or Christmas",
}

_model = None
_schema = None


def get_model():
    global _model, _schema
    if _model is None:
        _model = GLiNER2.from_pretrained(MODEL_NAME)
        _schema = _model.create_schema().entities(ENTITY_LABELS)
    return _model, _schema
