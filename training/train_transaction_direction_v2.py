"""Train and evaluate a candidate transaction/direction model with exact runtime math.

The exported artifact uses only the additive score contract implemented in
``src/python/transaction_direction.py`` and ``src/typescript/TransactionDirection.ts``.
It is an evaluation candidate and never replaces the legacy runtime model.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from preprocessing import PREPROCESSING_CONTRACT_VERSION, preprocess_message, tokenize_features
from transaction_direction import CONTRACT_VERSION, evaluate_model, validate_model


DATASET_PATH = ROOT / "data" / "training" / "dataset_expanded.json"
SPLIT_PATH = ROOT / "data" / "training" / "splits" / "transaction_direction_split.json"
FROZEN_FIXTURE_PATHS = (
    ROOT / "tests" / "fixtures" / "test_suite_cases.json",
    ROOT / "tests" / "fixtures" / "qa_adversarial_cases.json",
)
MODEL_PATH = ROOT / "data" / "models" / "masroof_transaction_direction_v2.json"
REPORT_PATH = ROOT / "data" / "reports" / "transaction_direction_v2_evaluation.json"

MODEL_VERSION = "2.0.0-candidate"
TRAINER_VERSION = "1.0.0"
SEED = 20261024
EPOCHS = 60
LEARNING_RATE = 0.08
L2_PENALTY = 0.0005
MIN_DOCUMENT_FREQUENCY = 2
TRANSACTION_THRESHOLD = 0.7
INCOME_THRESHOLD = 0.5
TRANSACTION_LABELS = {"TRANSACTION_DEBIT", "TRANSACTION_CREDIT"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _feature_counts(text: str, vocabulary: set[str] | None = None) -> Counter[str]:
    features = Counter(tokenize_features(preprocess_message(text)))
    if vocabulary is None:
        return features
    return Counter({feature: count for feature, count in features.items() if feature in vocabulary})


def _load_split(records: list[dict[str, Any]]) -> tuple[list[int], list[int], dict[str, Any]]:
    split = _load_json(SPLIT_PATH)
    if split.get("splitVersion") != "1.0.0":
        raise ValueError("unsupported transaction/direction split version")
    if split.get("preprocessingVersion") != PREPROCESSING_CONTRACT_VERSION:
        raise ValueError("split preprocessing version does not match runtime contract")
    if split.get("recordCount") != len(records):
        raise ValueError("split record count does not match dataset")
    if split.get("datasetSha256") != _sha256(DATASET_PATH):
        raise ValueError("split dataset hash does not match current dataset")

    train_indices = split.get("trainIndices")
    validation_indices = split.get("validationIndices")
    if not isinstance(train_indices, list) or not isinstance(validation_indices, list):
        raise ValueError("split indices must be lists")
    all_indices = train_indices + validation_indices
    if any(type(index) is not int or not 0 <= index < len(records) for index in all_indices):
        raise ValueError("split contains an invalid record index")
    if len(set(all_indices)) != len(records) or len(all_indices) != len(records):
        raise ValueError("split must cover every dataset record exactly once")
    return train_indices, validation_indices, split


def _build_vocabulary(records: list[dict[str, Any]], indices: Iterable[int]) -> set[str]:
    document_frequency: Counter[str] = Counter()
    for index in indices:
        document_frequency.update(_feature_counts(records[index]["text"]).keys())
    return {
        feature for feature, frequency in document_frequency.items()
        if frequency >= MIN_DOCUMENT_FREQUENCY
    }


def _train_head(
    examples: list[tuple[Counter[str], int]],
    vocabulary: set[str],
    seed_offset: int,
) -> tuple[float, dict[str, float]]:
    """Fit deterministic L2-regularized logistic regression with sparse SGD."""
    weights: defaultdict[str, float] = defaultdict(float)
    intercept = 0.0
    ordering = list(range(len(examples)))
    randomizer = random.Random(SEED + seed_offset)

    for epoch in range(EPOCHS):
        randomizer.shuffle(ordering)
        learning_rate = LEARNING_RATE / math.sqrt(1.0 + epoch * 0.12)
        for example_index in ordering:
            features, label = examples[example_index]
            logit = intercept + sum(weights[feature] * count for feature, count in features.items())
            probability = _sigmoid(logit)
            error = probability - label
            intercept -= learning_rate * error
            for feature, count in features.items():
                weights[feature] -= learning_rate * (error * count + L2_PENALTY * weights[feature])

    # Serializing every eligible feature makes scores deterministic even for an
    # unused feature and avoids implicit default-weight behavior in reports.
    return intercept, {feature: weights[feature] for feature in sorted(vocabulary)}


def _sigmoid(logit: float) -> float:
    if logit >= 0:
        return 1.0 / (1.0 + math.exp(-logit))
    exp_logit = math.exp(logit)
    return exp_logit / (1.0 + exp_logit)


def _binary_metrics(predicted: Iterable[bool], actual: Iterable[bool]) -> dict[str, Any]:
    tp = tn = fp = fn = 0
    for prediction, truth in zip(predicted, actual):
        if prediction and truth:
            tp += 1
        elif prediction:
            fp += 1
        elif truth:
            fn += 1
        else:
            tn += 1
    total = tp + tn + fp + fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "total": total,
        "truePositives": tp,
        "trueNegatives": tn,
        "falsePositives": fp,
        "falseNegatives": fn,
        "accuracy": (tp + tn) / total if total else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _direction_metrics(predicted: Iterable[str], actual: Iterable[str]) -> dict[str, Any]:
    predictions = list(predicted)
    truths = list(actual)
    total = len(truths)
    income_true = sum(truth == "INCOME" for truth in truths)
    income_predicted = sum(prediction == "INCOME" for prediction in predictions)
    income_correct = sum(prediction == truth == "INCOME" for prediction, truth in zip(predictions, truths))
    expense_correct = sum(prediction == truth == "EXPENSE" for prediction, truth in zip(predictions, truths))
    return {
        "total": total,
        "correct": income_correct + expense_correct,
        "accuracy": (income_correct + expense_correct) / total if total else 0.0,
        "incomeTrue": income_true,
        "incomePredicted": income_predicted,
        "incomeCorrect": income_correct,
        "expenseCorrect": expense_correct,
        "incomeAsExpense": sum(prediction == "EXPENSE" and truth == "INCOME" for prediction, truth in zip(predictions, truths)),
        "expenseAsIncome": sum(prediction == "INCOME" and truth == "EXPENSE" for prediction, truth in zip(predictions, truths)),
    }


def _evaluate_records(model: dict[str, Any], records: list[dict[str, Any]], indices: Iterable[int]) -> dict[str, Any]:
    selected = [records[index] for index in indices]
    decisions = [evaluate_model(model, tokenize_features(preprocess_message(record["text"]))) for record in selected]
    truths = [record["label"] in TRANSACTION_LABELS for record in selected]
    transaction = _binary_metrics((decision["isTransaction"] for decision in decisions), truths)

    positive_pairs = [
        (decision["type"], "INCOME" if record["label"] == "TRANSACTION_CREDIT" else "EXPENSE")
        for record, decision, truth in zip(selected, decisions, truths) if truth
    ]
    direction = _direction_metrics(
        (prediction for prediction, _ in positive_pairs),
        (truth for _, truth in positive_pairs),
    )

    provider_breakdown: dict[str, dict[str, Any]] = {}
    for provider in sorted({record["provider"] for record in selected}):
        provider_pairs = [
            (decision, record) for decision, record in zip(decisions, selected)
            if record["provider"] == provider
        ]
        provider_breakdown[provider] = _binary_metrics(
            (decision["isTransaction"] for decision, _ in provider_pairs),
            (record["label"] in TRANSACTION_LABELS for _, record in provider_pairs),
        )
    return {
        "transaction": transaction,
        "directionOnActualTransactions": direction,
        "providerBreakdown": provider_breakdown,
    }


def _fixture_cases(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    if isinstance(payload, dict) and isinstance(payload.get("testCases"), list):
        return payload["testCases"]
    if isinstance(payload, list):
        return payload
    raise ValueError(f"{path.name} is not a supported test fixture")


def _evaluate_frozen_corpus(model: dict[str, Any]) -> dict[str, Any]:
    cases = [case for path in FROZEN_FIXTURE_PATHS for case in _fixture_cases(path)]
    decisions = [evaluate_model(model, tokenize_features(preprocess_message(case["body"]))) for case in cases]
    truths = [case["expected"]["isValidTransaction"] for case in cases]
    transaction = _binary_metrics((decision["isTransaction"] for decision in decisions), truths)
    valid_pairs = [
        (decision["type"], case["expected"]["type"])
        for case, decision in zip(cases, decisions) if case["expected"]["isValidTransaction"]
    ]
    return {
        "scope": "model-only shared-contract scoring; it excludes runtime sender and regex guards",
        "transaction": transaction,
        "directionOnActualTransactions": _direction_metrics(
            (prediction for prediction, _ in valid_pairs),
            (truth for _, truth in valid_pairs),
        ),
    }


def main() -> int:
    records = _load_json(DATASET_PATH)
    if not isinstance(records, list) or not records:
        raise ValueError("dataset must be a non-empty list")
    if any(not isinstance(record, dict) or not isinstance(record.get("text"), str) or record.get("label") not in {
        "ANNOUNCEMENT", "CHAT_NOISE", "DECLINED", "OTP", "PROMO", "TRANSACTION_CREDIT", "TRANSACTION_DEBIT",
    } for record in records):
        raise ValueError("dataset records do not match the supported transaction/direction schema")

    train_indices, validation_indices, split = _load_split(records)
    vocabulary = _build_vocabulary(records, train_indices)
    cached_features = {
        index: _feature_counts(record["text"], vocabulary)
        for index, record in enumerate(records)
    }

    transaction_examples = [
        (cached_features[index], int(records[index]["label"] in TRANSACTION_LABELS))
        for index in train_indices
    ]
    direction_examples = [
        (cached_features[index], int(records[index]["label"] == "TRANSACTION_CREDIT"))
        for index in train_indices if records[index]["label"] in TRANSACTION_LABELS
    ]
    transaction_intercept, transaction_weights = _train_head(transaction_examples, vocabulary, seed_offset=0)
    direction_intercept, direction_weights = _train_head(direction_examples, vocabulary, seed_offset=1)

    model = {
        "contractVersion": CONTRACT_VERSION,
        "modelVersion": MODEL_VERSION,
        "preprocessingVersion": PREPROCESSING_CONTRACT_VERSION,
        "featureEncoding": "unigrams_then_adjacent_bigrams",
        "transaction": {
            "intercept": transaction_intercept,
            "threshold": TRANSACTION_THRESHOLD,
            "weights": transaction_weights,
        },
        "direction": {
            "intercept": direction_intercept,
            "incomeThreshold": INCOME_THRESHOLD,
            "weights": direction_weights,
        },
        "training": {
            "trainerVersion": TRAINER_VERSION,
            "seed": SEED,
            "epochs": EPOCHS,
            "learningRate": LEARNING_RATE,
            "l2Penalty": L2_PENALTY,
            "minimumDocumentFrequency": MIN_DOCUMENT_FREQUENCY,
            "datasetSha256": _sha256(DATASET_PATH),
            "splitVersion": split["splitVersion"],
            "splitSeed": split["seed"],
            "trainRecordCount": len(train_indices),
            "validationRecordCount": len(validation_indices),
            "vocabularySize": len(vocabulary),
        },
    }
    validate_model(model)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.write_text(json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = {
        "reportVersion": "1.0.0",
        "candidateModelPath": str(MODEL_PATH.relative_to(ROOT)).replace("\\", "/"),
        "candidateModelSha256": _sha256(MODEL_PATH),
        "evaluationScope": "candidate only; the legacy runtime remains active",
        "training": model["training"],
        "groupedValidation": _evaluate_records(model, records, validation_indices),
        "frozenCorpus": _evaluate_frozen_corpus(model),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    validation = report["groupedValidation"]
    print(f"Wrote candidate model: {MODEL_PATH}")
    print(f"Wrote evaluation report: {REPORT_PATH}")
    print(
        "Grouped validation transaction: "
        f"F1 {validation['transaction']['f1']:.4f}, "
        f"FP {validation['transaction']['falsePositives']}, "
        f"FN {validation['transaction']['falseNegatives']}"
    )
    print(
        "Grouped validation direction: "
        f"accuracy {validation['directionOnActualTransactions']['accuracy']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
