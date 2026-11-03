"""Versioned research completion features; preserve the original direction head."""
import json
from pathlib import Path
import re

from src.python.research.sms_semantics import CONTRACT as BASE, features as word_features, finite, normalize

CONTRACT_PATH = Path(__file__).resolve().parents[3] / "config/contracts/sms_completion_context.json"
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def features(text):
    words = re.findall(r"[^\W]+", normalize(text), re.UNICODE)
    return sorted({prefix + " ".join(words[i:i + size])
                   for size, prefix in zip(CONTRACT["lengths"], CONTRACT["prefixes"])
                   for i in range(len(words) - size + 1)})


def validate_model(model):
    if not isinstance(model, dict) or model.get("contractVersion") != CONTRACT["contractVersion"] or model.get("kind") != "completion_context" or set(model.get("heads", {})) != set(BASE["heads"]):
        raise ValueError("Invalid context model kind/version/heads")
    for name, head in model["heads"].items():
        vocabulary, weights = head.get("vocabulary"), head.get("weights")
        prefixes = tuple(CONTRACT["prefixes"]) if name == "completion" else ("w|",)
        if not isinstance(vocabulary, list) or any(not isinstance(x, str) or not x.startswith(prefixes) for x in vocabulary) or vocabulary != sorted(set(vocabulary)):
            raise ValueError("Invalid context vocabulary/order/encoding")
        if not isinstance(weights, list) or len(weights) != len(vocabulary) or any(not finite(x) for x in weights) or not finite(head.get("intercept")):
            raise ValueError("Invalid context flat weights/intercept")
        if head.get("labels") != BASE["heads"][name]:
            raise ValueError("Invalid context head labels")


class SmsCompletionContextModel:
    def __init__(self, model):
        validate_model(model)
        self.model = model
        self.indices = {name: {feature: i for i, feature in enumerate(head["vocabulary"])} for name, head in model["heads"].items()}

    def predict(self, text):
        emitted = {"completion": features(text), "direction": word_features(text, "word")}
        heads = {}
        for name, head in self.model["heads"].items():
            lookup = self.indices[name]
            active = sorted(lookup[x] for x in emitted[name] if x in lookup)
            score = float(head["intercept"])
            for index in active:
                score += head["weights"][index]
            if not finite(score):
                raise ValueError("Non-finite context score")
            heads[name] = {"activeIndices": active, "score": score, "prediction": head["labels"]["positive" if score > 0 else "negative"]}
        return {"normalized": normalize(text), "features": emitted, "heads": heads}
