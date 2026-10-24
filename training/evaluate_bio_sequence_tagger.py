"""Measure the BIO perceptron on a deterministic source-category holdout."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "training"))

from train_sequence_tagger import TAGS, TAG_TO_INDEX, evaluate, export_model, predict, train


DATA_PATH = ROOT / "data" / "training" / "bio_training_data.json"
REPORT_PATH = ROOT / "data" / "reports" / "bio_sequence_tagger_evaluation.json"
SEED = 20261024
VALIDATION_FRACTION = 0.20


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_examples(examples: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Keep each fixture source category in one deterministic split.

    Source categories are a coarse grouping proxy. The report records the
    selected groups so these metrics cannot be mistaken for template isolation.
    """
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for example in examples:
        groups[example["sourceCategory"]].append(example)
    entries = sorted(groups.items())
    randomizer = random.Random(SEED)
    randomizer.shuffle(entries)
    target = max(1, round(len(examples) * VALIDATION_FRACTION))
    selected: list[str] = []
    selected_count = 0
    for group_name, group_examples in entries:
        if selected_count >= target:
            break
        selected.append(group_name)
        selected_count += len(group_examples)
    validation_groups = set(selected)
    validation = [example for example in examples if example["sourceCategory"] in validation_groups]
    training = [example for example in examples if example["sourceCategory"] not in validation_groups]
    if not training or not validation:
        raise ValueError("BIO group split must contain train and validation examples")
    return training, validation, sorted(validation_groups)


def _spans(tag_indexes: Iterable[int]) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    active_label: str | None = None
    start = 0
    for index, tag_index in enumerate(tag_indexes):
        tag = TAGS[tag_index]
        if tag == "O":
            if active_label is not None:
                spans.append((active_label, start, index))
                active_label = None
            continue
        prefix, label = tag.split("-", 1)
        if prefix == "B" or active_label != label:
            if active_label is not None:
                spans.append((active_label, start, index))
            active_label = label
            start = index
    if active_label is not None:
        spans.append((active_label, start, index + 1))
    return spans


def _metric(tp: int, fp: int, fn: int) -> dict[str, Any]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "truePositives": tp,
        "falsePositives": fp,
        "falseNegatives": fn,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def entity_metrics(examples: Iterable[dict[str, Any]], model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    emission = {}
    for token, feature in model["featureIndex"].items():
        offset = feature * len(TAGS)
        for tag in range(len(TAGS)):
            weight = model["emissionWeights"][offset + tag]
            if weight:
                emission[(token, tag)] = weight
    transition = {
        (previous, tag): model["transitionWeights"][previous * len(TAGS) + tag]
        for previous in range(len(TAGS)) for tag in range(len(TAGS))
        if model["transitionWeights"][previous * len(TAGS) + tag]
    }
    totals: dict[str, Counter[str]] = defaultdict(Counter)
    for example in examples:
        predicted = Counter(_spans(predict(example["tokens"], emission, transition)))
        gold = Counter(_spans(TAG_TO_INDEX[tag] for tag in example["tags"]))
        for span, count in predicted.items():
            matched = min(count, gold.get(span, 0))
            totals[span[0]]["tp"] += matched
            totals[span[0]]["fp"] += count - matched
        for span, count in gold.items():
            totals[span[0]]["fn"] += count - min(count, predicted.get(span, 0))
    return {
        label: _metric(values["tp"], values["fp"], values["fn"])
        for label, values in sorted(totals.items())
    }


def main() -> int:
    artifact = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    examples = artifact.get("examples")
    if not isinstance(examples, list) or not examples:
        raise ValueError("BIO training artifact has no examples")
    if any(len(example.get("tokens", [])) != len(example.get("tags", [])) for example in examples):
        raise ValueError("BIO artifact has token/tag length mismatch")

    training, validation, validation_groups = split_examples(examples)
    emission, transition = train(training)
    model = export_model(training, emission, transition)
    exact, sequences, correct_tokens, total_tokens = evaluate(validation, model)
    report = {
        "reportVersion": "1.0.0",
        "datasetSha256": _sha256(DATA_PATH),
        "evaluationScope": "held-out source-category groups; coarse grouping proxy, not template isolation",
        "seed": SEED,
        "validationFractionTarget": VALIDATION_FRACTION,
        "trainingExampleCount": len(training),
        "validationExampleCount": len(validation),
        "validationSourceCategories": validation_groups,
        "tokenAccuracy": correct_tokens / total_tokens if total_tokens else 0.0,
        "exactSequenceAccuracy": exact / sequences if sequences else 0.0,
        "entityExactSpanMetrics": entity_metrics(validation, model),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote BIO held-out evaluation: {REPORT_PATH}")
    print(f"Holdout: {len(validation)} examples across {len(validation_groups)} source categories")
    print(f"Token accuracy: {report['tokenAccuracy']:.4f}; exact sequence accuracy: {report['exactSequenceAccuracy']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
