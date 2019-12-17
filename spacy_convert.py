from spacy.tokens import Doc, Span
from spacy.lang.de import German

nlp = German()

doc = Doc(
    nlp.vocab,
    words=["Here", "is", "an", "annotation", "."],
    spaces=[True, True, True, False, False]
)

Span(doc, 6, 18, label="Medication")
