"""Reusable averaged-perceptron learner for the isolated BIO experiments."""

from __future__ import annotations

import math
import random
import re
from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, List, Sequence, Tuple


from src.python.research.bio_sequence import TAGS, normalize_token
EPOCHS = 25
SEED = 20261024
TAG_TO_INDEX = {tag: index for index, tag in enumerate(TAGS)}

FeatureKey = Tuple[str, int]
TransitionKey = Tuple[int, int]


class AveragedWeights:
    """Sparse averaged-perceptron parameters with timestamped accumulation."""

    def __init__(self) -> None:
        self.weights: DefaultDict[tuple, float] = defaultdict(float)
        self.totals: DefaultDict[tuple, float] = defaultdict(float)
        self.timestamps: Dict[tuple, int] = {}
        self.step = 0

    def advance(self) -> None:
        self.step += 1

    def update(self, key: tuple, delta: float) -> None:
        if delta == 0:
            return
        previous_step = self.timestamps.get(key, 0)
        self.totals[key] += (self.step - previous_step) * self.weights[key]
        self.timestamps[key] = self.step
        self.weights[key] += delta

    def averaged(self) -> Dict[tuple, float]:
        if self.step == 0:
            return {}
        averaged: Dict[tuple, float] = {}
        for key, value in self.weights.items():
            total = self.totals[key] + (self.step - self.timestamps.get(key, 0)) * value
            mean = total / self.step
            if mean:
                averaged[key] = mean
        return averaged


def score_tag(
    token: str,
    previous_tag: int,
    tag: int,
    emission: Dict[FeatureKey, float],
    transition: Dict[TransitionKey, float],
    has_previous: bool,
) -> float:
    score = emission.get((token, tag), 0.0)
    if has_previous:
        score += transition.get((previous_tag, tag), 0.0)
    return score


def predict(
    tokens: Sequence[str],
    emission: Dict[FeatureKey, float],
    transition: Dict[TransitionKey, float],
) -> List[int]:
    predictions: List[int] = []
    previous_tag = 0
    for index, raw_token in enumerate(tokens):
        token = normalize_token(raw_token)
        best_tag = 0
        best_score = score_tag(token, previous_tag, 0, emission, transition, index > 0)
        for tag in range(1, len(TAGS)):
            score = score_tag(token, previous_tag, tag, emission, transition, index > 0)
            if score > best_score:
                best_tag = tag
                best_score = score
        predictions.append(best_tag)
        previous_tag = best_tag
    return predictions


def train(examples: Sequence[dict]) -> Tuple[Dict[FeatureKey, float], Dict[TransitionKey, float]]:
    emission_weights = AveragedWeights()
    transition_weights = AveragedWeights()
    order = list(range(len(examples)))
    randomizer = random.Random(SEED)

    for _ in range(EPOCHS):
        randomizer.shuffle(order)
        for example_index in order:
            example = examples[example_index]
            tokens = example["tokens"]
            gold_tags = [TAG_TO_INDEX[tag] for tag in example["tags"]]
            predicted_tags = predict(tokens, emission_weights.weights, transition_weights.weights)

            for index, (raw_token, gold_tag, predicted_tag) in enumerate(zip(tokens, gold_tags, predicted_tags)):
                emission_weights.advance()
                transition_weights.advance()
                if gold_tag == predicted_tag:
                    continue

                token = normalize_token(raw_token)
                emission_weights.update((token, gold_tag), 1.0)
                emission_weights.update((token, predicted_tag), -1.0)
                if index > 0:
                    transition_weights.update((gold_tags[index - 1], gold_tag), 1.0)
                    transition_weights.update((predicted_tags[index - 1], predicted_tag), -1.0)

    return emission_weights.averaged(), transition_weights.averaged()


def export_model(
    examples: Sequence[dict], emission: Dict[FeatureKey, float], transition: Dict[TransitionKey, float]
) -> dict:
    vocabulary = sorted({normalize_token(token) for example in examples for token in example["tokens"]})
    feature_index = {token: index for index, token in enumerate(vocabulary)}
    emission_weights = [0.0] * (len(vocabulary) * len(TAGS))
    for (token, tag), weight in emission.items():
        emission_weights[feature_index[token] * len(TAGS) + tag] = weight

    transition_weights = [0.0] * (len(TAGS) * len(TAGS))
    for (previous_tag, tag), weight in transition.items():
        transition_weights[previous_tag * len(TAGS) + tag] = weight

    model = {
        "version": "1.0.0",
        "tagCount": len(TAGS),
        "featureIndex": feature_index,
        "emissionWeights": emission_weights,
        "transitionWeights": transition_weights,
        "bias": [0.0] * len(TAGS),
        "metadata": {
            "algorithm": "averaged_perceptron",
            "tagScheme": "BIO",
            "tags": list(TAGS),
            "epochs": EPOCHS,
            "seed": SEED,
            "trainingExampleCount": len(examples),
            "normalization": "lowercase + Arabic diacritic/alef/yeh/teh-marbuta normalization",
        },
    }
    if not all(math.isfinite(weight) for weight in emission_weights + transition_weights):
        raise ValueError("Training produced a non-finite weight")
    return model


def evaluate(examples: Iterable[dict], model: dict) -> Tuple[int, int, int, int]:
    emission: Dict[FeatureKey, float] = {}
    for token, feature in model["featureIndex"].items():
        offset = feature * len(TAGS)
        for tag in range(len(TAGS)):
            weight = model["emissionWeights"][offset + tag]
            if weight:
                emission[(token, tag)] = weight
    transition = {
        (previous_tag, tag): model["transitionWeights"][previous_tag * len(TAGS) + tag]
        for previous_tag in range(len(TAGS))
        for tag in range(len(TAGS))
        if model["transitionWeights"][previous_tag * len(TAGS) + tag]
    }

    exact_sequences = total_sequences = correct_tokens = total_tokens = 0
    for example in examples:
        prediction = predict(example["tokens"], emission, transition)
        gold = [TAG_TO_INDEX[tag] for tag in example["tags"]]
        exact_sequences += int(prediction == gold)
        total_sequences += 1
        correct_tokens += sum(predicted == expected for predicted, expected in zip(prediction, gold))
        total_tokens += len(gold)
    return exact_sequences, total_sequences, correct_tokens, total_tokens
