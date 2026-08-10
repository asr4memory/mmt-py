"""Measure the running NER service against a gold annotation.

Sends examples/michael-kende-transcript.txt to the service and compares the
returned spans with examples/michael-kende-gold.json. Reports precision,
recall and F1, and lists the false positives and false negatives, so that a
change to the label descriptions in model.py can be judged by numbers instead
of by impression.

The service has to be running:

    uv run uvicorn api:app --reload

Usage:

    uv run python examples/evaluate.py
    uv run python examples/evaluate.py --per-segment
    uv run python examples/evaluate.py --url http://localhost:8000
"""

import argparse
import json
import string
import time
from collections import Counter
from pathlib import Path

import httpx

EXAMPLES = Path(__file__).parent
ARTICLES = ("the ", "a ", "an ", "der ", "die ", "das ", "den ", "dem ")
TITLES = ("dr. ", "prof. ", "professor ", "professorin ", "frau ", "herr ")


def normalize(text: str) -> str:
    """Lowercase, remove surrounding punctuation, remove leading articles and
    titles.

    The model returns spans over whole words, so a span carries whatever
    punctuation is attached to its first and last word ("FCC," and "Sprint.").
    Whether an article or an academic title is part of the span is a judgment
    call the model makes inconsistently, and the PER label counts a title used
    together with a name as part of the entity. None of these differences is an
    extraction error, so none of them should count as one.
    """
    text = text.lower().strip()
    text = text.strip(string.punctuation + string.whitespace)

    stripped = True
    while stripped:
        stripped = False
        for prefix in ARTICLES + TITLES:
            if text.startswith(prefix):
                text = text[len(prefix) :]
                stripped = True
    return text


def batches(transcript: Path, per_segment: bool) -> list[list[str]]:
    """The transcript as a single batch, or as one batch per segment.

    One batch per segment is what a caller gets by iterating over a
    transcript's segments. The single batch is sent to the model as one
    string.
    """
    lines = transcript.read_text().splitlines()
    if per_segment:
        return [line.split() for line in lines if line.split()]
    return [" ".join(lines).split()]


def extract(url: str, batches: list[list[str]]) -> list[tuple[str, str, float]]:
    """Post the batches to the service and return (label, text, score) tuples."""
    payload = {"batches": batches}

    started = time.monotonic()
    response = httpx.post(f"{url}/extract", json=payload, timeout=600)
    response.raise_for_status()
    elapsed = time.monotonic() - started

    entities = []
    for batch, spans in zip(batches, response.json()["results"]):
        for span in spans:
            words = " ".join(batch[span["start"] : span["end"]])
            entities.append((span["label"], normalize(words), span["score"]))

    print(f"{len(batches)} batch(es), {len(entities)} entities, {elapsed:.1f}s")
    return entities


def score(entities, gold, ignore):
    """Compare found entities with the gold annotation.

    Comparison is over multisets of (label, normalized text): an entity
    mentioned three times has to be found three times. Mentions listed in
    ignore are removed from the comparison instead of being counted either way.

    The threshold is not applied here. The service applies it, and entities
    below it never reach this function.
    """
    found = Counter((label, text) for label, text, _ in entities)
    found = Counter({key: n for key, n in found.items() if key not in ignore})

    true_positives = found & gold
    false_positives = found - gold
    false_negatives = gold - found

    hits = sum(true_positives.values())
    precision = hits / sum(found.values()) if found else 0.0
    recall = hits / sum(gold.values()) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1, false_positives, false_negatives


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        default="michael-kende",
        help="name of the transcript and gold pair in this directory, "
        "e.g. michael-kende or german",
    )
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--per-segment", action="store_true")
    parser.add_argument("--save", type=Path, help="write the entities to a JSON file")
    args = parser.parse_args()

    transcript = EXAMPLES / f"{args.dataset}-transcript.txt"
    annotation = json.loads((EXAMPLES / f"{args.dataset}-gold.json").read_text())
    gold = Counter(tuple(entry) for entry in annotation["gold"])
    ignore = {tuple(entry) for entry in annotation["ignore"]}

    entities = extract(args.url, batches(transcript, args.per_segment))
    precision, recall, f1, false_positives, false_negatives = score(
        entities, gold, ignore
    )

    print(f"precision {precision:.2f}  recall {recall:.2f}  f1 {f1:.2f}")

    scores = {(label, text): value for label, text, value in entities}
    if false_positives:
        print("\nfalse positives (found, not an entity):")
        for (label, text), count in sorted(false_positives.items()):
            print(f"  {label:5} {text:40} {scores[label, text]:.2f}  x{count}")
    if false_negatives:
        print("\nfalse negatives (missed):")
        for (label, text), count in sorted(false_negatives.items()):
            print(f"  {label:5} {text:40}       x{count}")

    if args.save:
        args.save.write_text(json.dumps(entities, indent=2))


if __name__ == "__main__":
    main()
