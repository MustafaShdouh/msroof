"""Float32 reference for the existing flat-word BIO runtime contract."""
import math
import re
import struct

TAGS = ("O", "B-AMT", "I-AMT", "B-CURR", "I-CURR", "B-MERCHANT", "I-MERCHANT", "B-ACCT", "I-ACCT", "B-BAL", "I-BAL")
NORMALIZATION_VERSION = "bio-word-1.0.0"
DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
ARABIC_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ـ": ""})


def normalize_token(token):
    return DIACRITICS.sub("", token.lower()).translate(ARABIC_MAP)


def float32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


class FlatBioModel:
    def __init__(self, model):
        count = len(TAGS)
        if model.get("version") != "1.0.0" or model.get("tagCount") != count:
            raise ValueError("Unsupported flat BIO contract")
        self.feature_index = model["featureIndex"]
        if (not isinstance(self.feature_index, dict) or any(not isinstance(key, str) for key in self.feature_index)
                or any(type(value) is not int for value in self.feature_index.values())
                or set(self.feature_index.values()) != set(range(len(self.feature_index)))):
            raise ValueError("BIO feature indexes must be contiguous integers")
        arrays = [model["emissionWeights"], model["transitionWeights"], model["bias"]]
        if [len(x) for x in arrays] != [len(self.feature_index) * count, count * count, count]:
            raise ValueError("BIO flat weight dimensions mismatch")
        if any(type(value) not in (int, float) or not math.isfinite(value) for array in arrays for value in array):
            raise ValueError("BIO weights must be finite numbers")
        try:
            converted = [[float32(value) for value in array] for array in arrays]
        except (OverflowError, struct.error) as error:
            raise ValueError("BIO weights must fit float32") from error
        if any(not math.isfinite(value) for array in converted for value in array):
            raise ValueError("BIO weights must fit finite float32")
        self.emission, self.transition, self.bias = converted

    def predict(self, tokens):
        predictions = []
        previous, count = 0, len(TAGS)
        for index, raw_token in enumerate(tokens):
            feature = self.feature_index.get(normalize_token(raw_token))
            scores = list(self.bias)
            if feature is not None:
                for tag in range(count):
                    scores[tag] = float32(scores[tag] + self.emission[feature * count + tag])
            if index:
                for tag in range(count):
                    scores[tag] = float32(scores[tag] + self.transition[previous * count + tag])
            previous = max(range(count), key=scores.__getitem__)
            predictions.append(previous)
        return predictions
