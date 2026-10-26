"""Standalone merchant-name research contract; not wired into SMS inference."""

import math
import re
import unicodedata

from ..preprocessing import normalize_financial_numbers

CONTRACT_VERSION = "merchant-name-category-1.0.0"


def normalize_name(text):
    if not isinstance(text, str):
        raise TypeError("Merchant name must be text")
    text = normalize_financial_numbers(unicodedata.normalize("NFKC", text)).lower()
    text = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", text)
    return re.sub(r"[^a-z0-9\u00c0-\u024f\u0621-\u064a]+", " ", text).strip()


def name_features(text):
    name = normalize_name(text)
    if not name:
        return []
    features = {"w:" + word for word in name.split()}
    padded = "^" + name + "$"
    for size in (3, 4, 5):
        features.update(f"c{size}:" + padded[i:i + size] for i in range(len(padded) - size + 1))
    return sorted(features)


def validate_model(model):
    if model.get("contractVersion") != CONTRACT_VERSION:
        raise ValueError("Unsupported merchant category contract")
    classes, features = model["classes"], model["features"]
    if not isinstance(classes, list) or not classes or any(not isinstance(x, str) or not x for x in classes) or len(set(classes)) != len(classes):
        raise ValueError("Invalid classes")
    if not isinstance(features, list) or any(not isinstance(x, str) or not x for x in features) or features != sorted(set(features)):
        raise ValueError("Features must be sorted and unique")
    for field, size in (("weights", len(features) * len(classes)), ("bias", len(classes)), ("classBusinessSupport", len(classes))):
        values = model[field]
        if not isinstance(values, list) or len(values) != size or any(type(x) not in (float, int) or not math.isfinite(x) for x in values):
            raise ValueError(f"Invalid {field}")
    if any(type(x) is not int or x < 1 for x in model["classBusinessSupport"]):
        raise ValueError("Invalid business support")
    policy = model["abstention"]
    for field in ("minScore", "minMargin", "minKnownFeatureFraction"):
        if type(policy.get(field)) not in (float, int) or not math.isfinite(policy[field]) or not 0 <= policy[field] <= 1:
            raise ValueError("Invalid abstention threshold")
    if type(policy.get("minClassBusinesses")) is not int or policy["minClassBusinesses"] < 1:
        raise ValueError("Invalid minimum class support")


def load_model(model):
    validate_model(model)
    return model, {feature: index for index, feature in enumerate(model["features"])}


def predict(loaded, text):
    model, index = loaded
    features = name_features(text)
    known = [index[feature] for feature in features if feature in index]
    fraction = len(known) / len(features) if features else 0.0
    logits = list(model["bias"])
    scale = 1 / math.sqrt(len(known)) if known else 0.0
    count = len(logits)
    for feature_id in known:
        for class_id in range(count):
            logits[class_id] += model["weights"][feature_id * count + class_id] * scale
    exp = [math.exp(value - max(logits)) for value in logits]
    total = sum(exp)
    scores = [value / total for value in exp]
    order = sorted(range(count), key=lambda i: (-scores[i], i))
    top = order[0]
    margin = scores[top] - (scores[order[1]] if count > 1 else 0)
    policy = model["abstention"]
    reason = ("no_features" if not features else "insufficient_feature_evidence" if not known or fraction < policy["minKnownFeatureFraction"] else
              "insufficient_class_support" if model["classBusinessSupport"][top] < policy["minClassBusinesses"] else
              "low_model_score" if scores[top] < policy["minScore"] else
              "small_margin" if margin < policy["minMargin"] else "accepted")
    return {"category": model["classes"][top] if reason == "accepted" else None,
            "topClass": model["classes"][top], "uncalibratedModelScore": scores[top],
            "margin": margin, "knownFeatureFraction": fraction, "reason": reason,
            "logits": logits, "scores": scores}
