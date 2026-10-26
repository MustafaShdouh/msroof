"""Exact additive transaction and direction model contract for training and parity tests."""

from __future__ import annotations

import math
from typing import Any, Iterable

CONTRACT_VERSION = "1.0.0"
FEATURE_ENCODING = "unigrams_then_adjacent_bigrams"


def _finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def validate_model(model: Any) -> None:
    if not isinstance(model, dict):
        raise ValueError("model must be an object")
    if model.get("contractVersion") != CONTRACT_VERSION:
        raise ValueError("unsupported transaction-direction contract version")
    if model.get("featureEncoding") != FEATURE_ENCODING:
        raise ValueError("unsupported feature encoding")
    for head_name, threshold_name in (("transaction", "threshold"), ("direction", "incomeThreshold")):
        head = model.get(head_name)
        if not isinstance(head, dict) or not _finite_number(head.get("intercept")):
            raise ValueError(f"{head_name} intercept must be finite")
        threshold = head.get(threshold_name)
        if not _finite_number(threshold) or not 0.0 < float(threshold) < 1.0:
            raise ValueError(f"{head_name} threshold must be between zero and one")
        weights = head.get("weights")
        if not isinstance(weights, dict) or any(not isinstance(key, str) or not _finite_number(value) for key, value in weights.items()):
            raise ValueError(f"{head_name} weights must map strings to finite numbers")


def sigmoid(logit: float) -> float:
    if logit >= 0:
        return 1.0 / (1.0 + math.exp(-logit))
    exp_logit = math.exp(logit)
    return exp_logit / (1.0 + exp_logit)


def score_head(head: dict[str, Any], features: Iterable[str]) -> tuple[float, float]:
    logit = float(head["intercept"])
    weights = head["weights"]
    for feature in features:
        logit += float(weights.get(feature, 0.0))
    return logit, sigmoid(logit)


def evaluate_model(model: dict[str, Any], features: Iterable[str]) -> dict[str, Any]:
    validate_model(model)
    feature_list = list(features)
    transaction_logit, transaction_probability = score_head(model["transaction"], feature_list)
    direction_logit, income_probability = score_head(model["direction"], feature_list)
    is_transaction = transaction_probability >= float(model["transaction"]["threshold"])
    transaction_type = "INCOME" if income_probability >= float(model["direction"]["incomeThreshold"]) else "EXPENSE"
    return {
        "transactionLogit": transaction_logit,
        "transactionProbability": transaction_probability,
        "isTransaction": is_transaction,
        "directionLogit": direction_logit,
        "incomeProbability": income_probability,
        "type": transaction_type,
    }
