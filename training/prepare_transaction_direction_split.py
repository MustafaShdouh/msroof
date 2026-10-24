"""Create a deterministic template-group split for transaction/direction training."""

from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))
from preprocessing import PREPROCESSING_CONTRACT_VERSION, preprocess_message


DATASET_PATH = ROOT / "data" / "training" / "dataset_expanded.json"
OUTPUT_PATH = ROOT / "data" / "training" / "splits" / "transaction_direction_split.json"
SEED = 20261024
VALIDATION_FRACTION = 0.20
SPLIT_VERSION = "1.0.0"
ACCOUNT_MASK = re.compile(r"(?:[0-9]{2,4}\*[0-9]{2,4}|xxxx[0-9]{3,4}|\*[0-9]{4})", re.IGNORECASE)
NUMBER = re.compile(r"\b\d+(?:[,.']\d+)*\b")


def template_signature(record: dict) -> str:
    """Mask variable values so one generated template stays in one split."""
    text = record["text"]
    merchant = record.get("expected_merchant")
    if merchant:
        text = re.sub(re.escape(str(merchant)), " MERCHANT ", text, flags=re.IGNORECASE)
    text = ACCOUNT_MASK.sub(" ACCOUNT ", text)
    text = NUMBER.sub(" NUMBER ", text)
    return f"{record['provider']}|{record['label']}|{preprocess_message(text)}"


def build_split(records: list[dict]) -> dict:
    groups_by_label: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    signatures: list[str] = []
    for index, record in enumerate(records):
        signature = template_signature(record)
        signatures.append(signature)
        groups_by_label[record["label"]][signature].append(index)

    validation_indices: set[int] = set()
    randomizer = random.Random(SEED)
    for label, groups in sorted(groups_by_label.items()):
        entries = sorted(groups.items())
        randomizer.shuffle(entries)
        target = max(1, round(sum(len(indexes) for _, indexes in entries) * VALIDATION_FRACTION))
        selected = 0
        for _, indexes in entries:
            if selected >= target:
                break
            validation_indices.update(indexes)
            selected += len(indexes)

    train_indices = [index for index in range(len(records)) if index not in validation_indices]
    validation_list = sorted(validation_indices)
    train_signatures = {signatures[index] for index in train_indices}
    validation_signatures = {signatures[index] for index in validation_list}
    overlap = train_signatures.intersection(validation_signatures)
    if overlap:
        raise ValueError("Template groups overlap between train and validation")

    label_counts: dict[str, dict[str, int]] = {}
    for label in sorted(groups_by_label):
        label_counts[label] = {
            "train": sum(records[index]["label"] == label for index in train_indices),
            "validation": sum(records[index]["label"] == label for index in validation_list),
            "templateGroups": len(groups_by_label[label]),
        }
    return {
        "splitVersion": SPLIT_VERSION,
        "seed": SEED,
        "validationFraction": VALIDATION_FRACTION,
        "preprocessingVersion": PREPROCESSING_CONTRACT_VERSION,
        "recordCount": len(records),
        "trainIndices": train_indices,
        "validationIndices": validation_list,
        "trainTemplateGroupCount": len(train_signatures),
        "validationTemplateGroupCount": len(validation_signatures),
        "labelCounts": label_counts,
    }


def main() -> None:
    raw_dataset = DATASET_PATH.read_bytes()
    records = json.loads(raw_dataset)
    if not isinstance(records, list) or not records:
        raise ValueError("dataset_expanded.json must contain a non-empty list")
    required = {"text", "label", "provider", "expected_merchant"}
    if any(not required.issubset(record) for record in records):
        raise ValueError("dataset records do not match the required training schema")
    artifact = build_split(records)
    artifact["datasetSha256"] = hashlib.sha256(raw_dataset).hexdigest()
    OUTPUT_PATH.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Saved {OUTPUT_PATH.name}: {len(artifact['trainIndices'])} train, {len(artifact['validationIndices'])} validation")
    print(f"Template groups: {artifact['trainTemplateGroupCount']} train, {artifact['validationTemplateGroupCount']} validation")


if __name__ == "__main__":
    main()
