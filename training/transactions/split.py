"""Validate the frozen global sanitized split; never regenerate provider-local folds."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from training.corpus_io import DATASET, load_development_split


def main():
    records = json.loads(DATASET.read_text(encoding="utf-8"))
    train, validation, split = load_development_split(records)
    print(f"Frozen sanitized split valid: {len(train)} train / {len(validation)} validation; {len(split['groups'])} global groups. No files changed.")


if __name__ == "__main__":
    main()
