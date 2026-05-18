import argparse
import json
from pathlib import Path

from extract import enrich_transcript

parser = argparse.ArgumentParser(description="Enrich a transcript JSON file with NER annotations.")
parser.add_argument("input", type=Path, help="Path to the transcript JSON file")
args = parser.parse_args()

with args.input.open(encoding="utf-8") as f:
    transcript = json.load(f)

enriched = enrich_transcript(transcript)

output = args.input.with_stem(args.input.stem + "_ner_enriched")
with output.open("w", encoding="utf-8") as f:
    json.dump(enriched, f, ensure_ascii=False, indent=4)

print(f"Written to {output}")
