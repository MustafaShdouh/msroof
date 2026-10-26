"""Isolated multi-feature BIO research contract; active extraction is unchanged."""
import math
import re
from .bio_sequence import TAGS, normalize_token, float32
from ..preprocessing import normalize_financial_numbers

VERSION = "2.0.0"
FEATURE_CONTRACT = "bio-context-1.0.0"
NUMERIC = re.compile(r"[0-9]+(?:[.,'’][0-9]+)*")
MASK = re.compile(r"[0-9*x]+")
WORD = re.compile(r"[a-z\u0621-\u064a]+")


def token_parts(raw):
    value = normalize_token(normalize_financial_numbers(raw))
    digits = sum("0" <= char <= "9" for char in value)
    if digits and MASK.fullmatch(value) and ("*" in value or "x" in value):
        return "<MASK>", ["mask", "digits:" + str(min(digits, 8))]
    if NUMERIC.fullmatch(value):
        shape = ["number", "digits:" + str(min(digits, 8))]
        final = re.search(r"[.,]([0-9]+)$", value)
        if final:
            shape.append("fraction:" + str(min(len(final[1]), 4)))
        else:
            shape.append("integer" if value.isascii() and value.isdigit() else "grouped")
        return "<NUMBER>", shape
    if WORD.fullmatch(value):
        return value, ["word"]
    return value, ["punct" if value and all(not char.isalnum() for char in value) else "mixed"]


def sequence_features(tokens):
    parts = [token_parts(token) for token in tokens]
    result = []
    for index, (word, shape) in enumerate(parts):
        features = ["bias", "w0=" + word] + ["s0=" + item for item in shape]
        for offset in (-2, -1, 1, 2):
            at = index + offset
            neighbor = parts[at][0] if 0 <= at < len(parts) else ("<BOS>" if at < 0 else "<EOS>")
            features.append("w" + str(offset) + "=" + neighbor)
        for offset in (-1, 1):
            at = index + offset
            shapes = parts[at][1] if 0 <= at < len(parts) else ["BOS" if at < 0 else "EOS"]
            features.extend("s" + str(offset) + "=" + item for item in shapes)
        result.append(features)
    return result


def legal_tag(tag, previous):
    return tag == 0 or tag % 2 == 1 or previous in (tag - 1, tag)


def best_legal(scores, previous):
    return max((tag for tag in range(len(TAGS)) if legal_tag(tag, previous)), key=scores.__getitem__)


def rounded_add(left, right):
    value = left + right
    try:
        return float32(value)
    except OverflowError:
        # Float32Array assignment overflows to infinity in JavaScript.
        return math.copysign(math.inf, value)


class ContextBioModel:
    def __init__(self, model):
        if (model.get("version") != VERSION or model.get("featureContract") != FEATURE_CONTRACT
                or model.get("tags") != list(TAGS)):
            raise ValueError("Unsupported context BIO model contract")
        index = model.get("featureIndex")
        if (not isinstance(index, dict) or any(not isinstance(key, str) for key in index)
                or any(type(value) is not int for value in index.values())
                or set(index.values()) != set(range(len(index)))):
            raise ValueError("Context BIO feature indexes must be contiguous")
        self.feature_index = dict(index)
        arrays = [model.get("emissionWeights"), model.get("transitionWeights")]
        if (not all(isinstance(array, list) for array in arrays)
                or [len(array) for array in arrays] != [len(index) * len(TAGS), len(TAGS) ** 2]):
            raise ValueError("Context BIO weight dimensions mismatch")
        if any(type(value) not in (int, float) or not math.isfinite(value) for array in arrays for value in array):
            raise ValueError("Context BIO weights must be finite numbers")
        try:
            converted = [[float32(value) for value in array] for array in arrays]
        except OverflowError as error:
            raise ValueError("Context BIO weights must fit float32") from error
        if any(not math.isfinite(value) for array in converted for value in array):
            raise ValueError("Context BIO weights must fit float32")
        self.emission, self.transition = converted

    def predict(self, tokens):
        output, previous, count = [], None, len(TAGS)
        for features in sequence_features(tokens):
            scores = [0.] * count
            for feature in features:
                index = self.feature_index.get(feature)
                if index is not None:
                    for tag in range(count):
                        scores[tag] = rounded_add(scores[tag], self.emission[index * count + tag])
            if previous is not None:
                for tag in range(count):
                    scores[tag] = rounded_add(scores[tag], self.transition[previous * count + tag])
            previous = best_legal(scores, previous)
            output.append(previous)
        return output
