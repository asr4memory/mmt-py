"""Measure the NER extraction against a gold annotation.

Runs the extraction on examples/michael-kende-transcript.txt in this process
and compares the returned spans with examples/michael-kende-gold.json. Reports precision,
recall and F1, and lists the false positives and false negatives, so that a
change to the label descriptions in model.py can be judged by numbers instead
of by impression.

Usage:

    uv run python examples/evaluate.py
    uv run python examples/evaluate.py --per-segment
    uv run python examples/evaluate.py --window 72 --overlap 16 --threshold 0.4
    uv run python examples/evaluate.py --no-window --threshold 0.5
"""

import argparse
import json
import string
import time
from collections import Counter
import sys
from pathlib import Path

EXAMPLES = Path(__file__).parent

# The script lives in examples/, so the service modules are not on the path.
sys.path.insert(0, str(EXAMPLES.parent))

from extraction import extract as extract_spans  # noqa: E402
from windowing import OVERLAP, WINDOW  # noqa: E402
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
    transcript's segments. The single batch gives the model the full context
    and is split into overlapping windows by the extraction.
    """
    lines = transcript.read_text().splitlines()
    if per_segment:
        return [line.split() for line in lines if line.split()]
    return [" ".join(lines).split()]


def extract(batches: list[list[str]], settings: dict) -> list[tuple[str, str, float]]:
    """Run the extraction on the batches and return (label, text, score) tuples.

    settings holds only those keyword arguments that were given on the command
    line. Every other argument is left out, so the extraction applies its own
    default and the evaluation measures it as the NER task runs it.
    """
    started = time.monotonic()
    results = extract_spans(batches, **settings)
    elapsed = time.monotonic() - started

    entities = []
    for batch, spans in zip(batches, results):
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

    The threshold is not applied here. The model applies it, and entities
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
    parser.add_argument("--per-segment", action="store_true")
    parser.add_argument(
        "--threshold",
        type=float,
        help="override the default threshold",
    )
    windowing = parser.add_mutually_exclusive_group()
    windowing.add_argument(
        "--window",
        type=int,
        help="override the default window size, in words. Window size "
        "and threshold are tuned together, so this is usually given together "
        "with --threshold",
    )
    windowing.add_argument(
        "--no-window",
        action="store_true",
        help="switch the windowing off, so that each batch is sent "
        "to the model as one string however long it is",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        help="override the number of words consecutive windows share",
    )
    parser.add_argument("--save", type=Path, help="write the entities to a JSON file")
    args = parser.parse_args()

    settings = {}
    if args.threshold is not None:
        settings["threshold"] = args.threshold
    if args.no_window:
        settings["window"] = None
    elif args.window is not None:
        settings["window"] = args.window
    if args.overlap is not None:
        settings["overlap"] = args.overlap
    window = settings.get("window", WINDOW)
    overlap = settings.get("overlap", OVERLAP)
    if window is not None and not 0 <= overlap < window:
        parser.error("the overlap must be at least 0 and smaller than the window")

    transcript = EXAMPLES / f"{args.dataset}-transcript.txt"
    annotation = json.loads((EXAMPLES / f"{args.dataset}-gold.json").read_text())
    gold = Counter(tuple(entry) for entry in annotation["gold"])
    ignore = {tuple(entry) for entry in annotation["ignore"]}

    entities = extract(batches(transcript, args.per_segment), settings)
    precision, recall, f1, false_positives, false_negatives = score(
        entities, gold, ignore
    )

    used = json.dumps(settings) if settings else "defaults"
    print(f"{used}  precision {precision:.2f}  recall {recall:.2f}  f1 {f1:.2f}")

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
