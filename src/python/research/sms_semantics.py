"""Research-only binary word/character features and flat float64 head evaluation."""
import json
import math
from pathlib import Path
import re
import unicodedata

from src.python.preprocessing import normalize_financial_numbers

CONTRACT_PATH = Path(__file__).resolve().parents[3] / "config/contracts/sms_semantics_model.json"
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
NUMBER = re.compile(CONTRACT["numericPattern"])
SPACE = re.compile(CONTRACT["whitespacePattern"])


def normalize(text):
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    value = normalize_financial_numbers(unicodedata.normalize("NFC", text)).replace("\\n", "\n").replace("\r", "")
    if value.startswith("JO\n"):
        value = value[3:]
    value = re.sub(r"[\u064b-\u065f\u0670]", "", value)
    value = re.sub(r"[A-Z]", lambda match: match[0].lower(), value)
    return SPACE.sub(" ", NUMBER.sub(" num ", value)).strip(" ")


def features(text, arm):
    if arm not in CONTRACT["arms"]:
        raise ValueError("Unsupported research arm")
    value, words, current = normalize(text), [], []
    for char in value + " ":
        if char.isalnum() or char == "_":
            current.append(char)
        elif current:
            words.append("".join(current))
            current = []
    result = {"w|" + word for word in words}
    if arm == "word_char":
        for length in (3, 4, 5):
            result.update(f"c{length}|" + value[index:index + length] for index in range(len(value) - length + 1))
    return sorted(result)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_model(model):
    if not isinstance(model, dict) or model.get("contractVersion") != CONTRACT["contractVersion"] or model.get("arm") not in CONTRACT["arms"] or set(model.get("heads", {})) != set(CONTRACT["heads"]):
        raise ValueError("Invalid research model/version/arm/heads")
    for name, head in model["heads"].items():
        vocabulary, weights = head.get("vocabulary"), head.get("weights")
        if not isinstance(vocabulary, list) or any(not isinstance(feature, str) for feature in vocabulary) or vocabulary != sorted(set(vocabulary)):
            raise ValueError("Vocabulary must be distinct code-point-sorted strings")
        prefixes = ("w|",) if model["arm"] == "word" else ("w|", "c3|", "c4|", "c5|")
        if any(not feature.startswith(prefixes) for feature in vocabulary):
            raise ValueError("Feature encoding does not match arm")
        if not isinstance(weights, list) or len(weights) != len(vocabulary) or any(not finite(weight) for weight in weights) or not finite(head.get("intercept")):
            raise ValueError("Flat weights/intercept must be finite and aligned")
        if head.get("labels") != CONTRACT["heads"][name]:
            raise ValueError("Head labels differ from fixed contract")


class SmsSemanticsModel:
    def __init__(self, model):
        validate_model(model)
        self.model = model
        self.indices = {name: {feature: index for index, feature in enumerate(head["vocabulary"])} for name, head in model["heads"].items()}

    def predict(self, text):
        emitted = features(text, self.model["arm"])
        output = {}
        for name, head in self.model["heads"].items():
            indices = self.indices[name]
            active = sorted(indices[feature] for feature in emitted if feature in indices)
            score = float(head["intercept"])
            for index in active:
                score += head["weights"][index]
            if not math.isfinite(score):
                raise ValueError("Non-finite accumulated score")
            output[name] = {"activeIndices": active, "score": score, "prediction": head["labels"]["positive" if score > 0 else "negative"]}
        return {"normalized": normalize(text), "features": emitted, "heads": output}
