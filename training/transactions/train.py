"""Train and evaluate a candidate transaction/direction model with exact runtime math.

The exported artifact uses only the additive score contract implemented in
``src/python/research/transaction_direction.py`` and ``src/typescript/research/TransactionDirection.ts``.
It is an evaluation candidate and never replaces the legacy runtime model.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.python.preprocessing import PREPROCESSING_CONTRACT_VERSION, preprocess_message, tokenize_features
from src.python.research.transaction_direction import CONTRACT_VERSION, evaluate_model, validate_model
from training.corpus_io import DATASET, SPLIT, FIXTURES, load_development_split, write_immutable


DATASET_PATH = DATASET
SPLIT_PATH = SPLIT
FROZEN_FIXTURE_PATHS = (
    FIXTURES / "test_suite_cases.json",
    FIXTURES / "qa_adversarial_cases.json",
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
OPTIMIZER = "sgd"


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
    return load_development_split(records, DATASET_PATH, SPLIT_PATH)


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
    if OPTIMIZER == "liblinear":
        import numpy as np
        from sklearn.feature_extraction import DictVectorizer
        from sklearn.linear_model import LogisticRegression
        vectorizer = DictVectorizer(sort=True)
        matrix = vectorizer.fit_transform([dict(features) for features, _ in examples])
        if matrix.nnz >= 2 ** 31 or max(matrix.shape) >= 2 ** 31:
            raise ValueError("liblinear candidate exceeds 32-bit sparse index capacity")
        matrix.indices = matrix.indices.astype(np.int32)
        matrix.indptr = matrix.indptr.astype(np.int32)
        labels = [label for _, label in examples]
        classifier = LogisticRegression(solver="liblinear", C=1.0, max_iter=2000, random_state=SEED + seed_offset)
        classifier.fit(matrix, labels)
        learned = dict(zip(vectorizer.get_feature_names_out(), classifier.coef_[0].tolist()))
        # The exported head scores exactly the same counted features; there is
        # no TF-IDF normalization or training-only scaling hidden in this path.
        return float(classifier.intercept_[0]), {feature: float(learned.get(feature, 0)) for feature in sorted(vocabulary)}
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", help="New candidate version; required to fit (letters/digits/underscores)")
    parser.add_argument("--check-inputs", action="store_true", help="Validate corpus and split without fitting")
    parser.add_argument("--optimizer", choices=("sgd", "liblinear"), default="sgd")
    args = parser.parse_args()
    global OPTIMIZER
    OPTIMIZER = args.optimizer
    records = _load_json(DATASET_PATH)
    if not isinstance(records, list) or not records:
        raise ValueError("dataset must be a non-empty list")
    if any(not isinstance(record, dict) or not isinstance(record.get("text"), str) or record.get("label") not in {
        "ANNOUNCEMENT", "CHAT_NOISE", "DECLINED", "OTP", "PROMO", "TRANSACTION_CREDIT", "TRANSACTION_DEBIT",
    } for record in records):
        raise ValueError("dataset records do not match the supported transaction/direction schema")

    train_indices, validation_indices, split = _load_split(records)
    if args.check_inputs:
        print(f"Sanitized inputs valid: {len(train_indices)} train / {len(validation_indices)} validation; no fitting")
        return 0
    import re
    if not args.run_id or not re.fullmatch(r"[a-z0-9_]{1,40}", args.run_id):
        parser.error("A new --run-id is required to fit a candidate")
    global MODEL_PATH, REPORT_PATH
    MODEL_PATH = ROOT / f"data/models/transaction_direction_{args.run_id}_candidate.json"
    REPORT_PATH = ROOT / f"data/reports/transaction_direction_{args.run_id}_evaluation.json"
    if MODEL_PATH.exists() or REPORT_PATH.exists():
        raise ValueError("Candidate outputs already exist; select a new run ID")
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
            "optimizer": OPTIMIZER,
            "optimizerParameters": ({"solver": "liblinear", "C": 1.0, "maxIterations": 2000} if OPTIMIZER == "liblinear" else
                                    {"epochs": EPOCHS, "learningRate": LEARNING_RATE, "l2Penalty": L2_PENALTY}),
            "corpusVersion": split["corpusVersion"],
            "splitSha256": _sha256(SPLIT_PATH),
            "scope": "Synthetic development candidate; no independent accuracy claim",
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
    if OPTIMIZER == "liblinear":
        import sklearn
        model["training"]["sklearnVersion"] = sklearn.__version__
        # The old SGD fields are not the optimizer settings for this candidate.
        for key in ("epochs", "learningRate", "l2Penalty"):
            del model["training"][key]
    validate_model(model)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_immutable(MODEL_PATH, json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
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
    write_immutable(REPORT_PATH, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

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
