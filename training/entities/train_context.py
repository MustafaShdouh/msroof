"""Fit one approved context/shape BIO trial on the frozen 63/16 development split."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from training.corpus_io import sha256, write_immutable, snapshot_report_inputs
from training.entities.evaluate import prepare_evaluation, metrics, regex_value_metrics
from training.entities.prepare_labels import DATA, SPLIT, REPORT as LABEL_REPORT, POLICY
from training.entities.perceptron import AveragedWeights, EPOCHS, SEED
from src.python.research.bio_sequence import TAGS
from src.python.research.bio_context import VERSION, FEATURE_CONTRACT, sequence_features, best_legal, ContextBioModel
from tools.node_runtime import node_executable

CONTRACT = ROOT / "config/contracts/bio_context_model.json"
WORD_MODEL = ROOT / "data/models/bio_labels_v2_word_v1_candidate.json"
WORD_REPORT = ROOT / "data/reports/bio/labels_v2_word_v1_evaluation.json"


def predict_training(features_by_token, emission, transition):
    previous, output = None, []
    for features in features_by_token:
        scores = [sum(emission.get((feature, tag), 0.) for feature in features) for tag in range(len(TAGS))]
        if previous is not None:
            for tag in range(len(TAGS)):
                scores[tag] += transition.get((previous, tag), 0.)
        previous = best_legal(scores, previous)
        output.append(previous)
    return output


def fit(training):
    emission, transition = AveragedWeights(), AveragedWeights()
    prepared = [(sequence_features(row["tokens"]), [TAGS.index(tag) for tag in row["tags"]]) for row in training]
    order, randomizer = list(range(len(prepared))), random.Random(SEED)
    for _ in range(EPOCHS):
        randomizer.shuffle(order)
        for index in order:
            features_by_token, gold = prepared[index]
            predictions = predict_training(features_by_token, emission.weights, transition.weights)
            for at, (features, expected, actual) in enumerate(zip(features_by_token, gold, predictions)):
                emission.advance()
                transition.advance()
                if expected != actual:
                    for feature in features:
                        emission.update((feature, expected), 1.)
                        emission.update((feature, actual), -1.)
                    if at:
                        transition.update((gold[at - 1], expected), 1.)
                        transition.update((predictions[at - 1], actual), -1.)
    emission_weights, transition_weights = emission.averaged(), transition.averaged()
    vocabulary = sorted({feature for features, _ in prepared for token in features for feature in token})
    index = {feature: at for at, feature in enumerate(vocabulary)}
    return {"version": VERSION, "featureContract": FEATURE_CONTRACT, "tags": list(TAGS), "featureIndex": index,
            "emissionWeights": [emission_weights.get((feature, tag), 0.) for feature in vocabulary for tag in range(len(TAGS))],
            "transitionWeights": [transition_weights.get((previous, tag), 0.) for previous in range(len(TAGS)) for tag in range(len(TAGS))],
            "metadata": {"algorithm": "averaged_perceptron", "epochs": EPOCHS, "seed": SEED, "trainingCount": len(training),
                         "featureContractSha256": sha256(CONTRACT), "datasetSha256": sha256(DATA), "splitSha256": sha256(SPLIT),
                         "runtimeScoreDtype": "float32 per addition", "productionIntegrated": False}}


def coverage(training, validation):
    vocabulary = {feature for row in training for token in sequence_features(row["tokens"]) for feature in token}
    total, unknown = Counter(), Counter()
    for row in validation:
        for features, tag in zip(sequence_features(row["tokens"]), row["tags"]):
            total[tag] += 1
            unknown[tag] += not any(feature in vocabulary and feature.startswith("s0=") for feature in features)
    return {tag: {"tokens": total[tag], "withoutKnownCurrentShape": unknown[tag]} for tag in sorted(total)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_]{1,40}", args.run_id):
        parser.error("Invalid run ID")
    training, validation, split = prepare_evaluation()
    model_path = ROOT / f"data/models/bio_context_{args.run_id}_candidate.json"
    report_path = ROOT / f"data/reports/bio/context_{args.run_id}_evaluation.json"
    if args.check:
        model = json.loads(model_path.read_text(encoding="utf-8"))
    else:
        if model_path.exists() or report_path.exists():
            raise ValueError("Trial already exists; use --check or a new run ID")
        model = fit(training)
    for key, path in (("datasetSha256", DATA), ("splitSha256", SPLIT), ("featureContractSha256", CONTRACT)):
        if model["metadata"][key] != sha256(path):
            raise ValueError("Candidate identifies different data or feature contract")
    runtime = ContextBioModel(model)
    predictions = [runtime.predict(row["tokens"]) for row in validation]
    examples = [row["tokens"] for row in validation]
    process = subprocess.run([node_executable(), str(ROOT / "tools/evaluation/probe_bio_context.ts")],
                             input=json.dumps({"model": model, "examples": examples}), capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if process.returncode:
        raise ValueError("Context BIO TypeScript probe failed: " + process.stderr)
    actual = json.loads(process.stdout)
    if actual["predictions"] != predictions or actual["features"] != [sequence_features(tokens) for tokens in examples]:
        raise ValueError("Python/TypeScript context features or predictions differ")
    baseline = json.loads(WORD_REPORT.read_text(encoding="utf-8"))
    if (baseline["candidateModelSha256"] != sha256(WORD_MODEL)
            or baseline["inputSha256"][SPLIT.relative_to(ROOT).as_posix()] != sha256(SPLIT)
            or baseline["inputSha256"][DATA.relative_to(ROOT).as_posix()] != sha256(DATA)):
        raise ValueError("Word comparator is not bound to the same frozen data")
    source_paths = [DATA, SPLIT, LABEL_REPORT, POLICY, CONTRACT, WORD_MODEL, WORD_REPORT,
                    ROOT / "training/entities/perceptron.py", ROOT / "training/entities/evaluate.py", ROOT / "training/entities/prepare_labels.py",
                    ROOT / "training/evaluation/behavior.py", ROOT / "training/corpus_io.py", Path(__file__),
                    ROOT / "src/python/research/bio_context.py", ROOT / "src/python/research/bio_sequence.py", ROOT / "src/python/preprocessing.py",
                    ROOT / "src/python/entity_text.py", ROOT / "src/python/engine.py", ROOT / "src/python/legacy_transaction_model.py",
                    ROOT / "src/python/service_notice.py", ROOT / "config/contracts/service_notice.json", ROOT / "data/models/masroof_model.json",
                    ROOT / "src/python/authorization_request.py", ROOT / "config/contracts/authorization_request.json",
                    ROOT / "src/typescript/research/BioContext.ts", ROOT / "src/typescript/research/BioNormalization.ts", ROOT / "src/typescript/Preprocessing.ts",
                    ROOT / "tools/evaluation/probe_bio_context.ts"]
    hashes = {path.relative_to(ROOT).as_posix(): sha256(path) for path in source_paths}
    result = metrics(validation, predictions)
    slices = {}
    for name, arabic in (("arabic_script_present", True), ("no_arabic_script", False)):
        selected = [(row, prediction) for row, prediction in zip(validation, predictions) if bool(re.search(r"[\u0621-\u064a]", row["text"])) == arabic]
        slices[name] = metrics([row for row, _ in selected], [prediction for _, prediction in selected])
    old = baseline["bio"]
    numeric_better = all(result["perEntityCharacterSpan"][label]["recall"] > old["perEntityCharacterSpan"][label]["recall"] for label in ("AMT", "BAL"))
    more_complete = result["exactPrimaryFields"]["count"] > old["exactPrimaryFields"]["count"]
    model_text = json.dumps(model, ensure_ascii=False, separators=(',', ':'))
    report = {"version": "1.0.0", "scope": "Approved context/shape research, exposed synthetic development; not independent accuracy",
              "inputSha256": hashes, "candidateModelSha256": hashlib.sha256(model_text.encode()).hexdigest(),
              "training": {"count": len(training), "epochs": EPOCHS, "seed": SEED, "validationBasedSearch": False, "augmentation": False},
              "validationCount": len(validation), "quarantineCount": len(split["quarantinedIds"]),
              "parity": {"featuresAndPredictions": True, "examples": len(validation), "dtype": "float32 per addition"},
              "bio": result, "wordComparator": old, "regexValues": regex_value_metrics(validation), "scriptSlices": slices,
              "validationShapeCoverage": coverage(training, validation),
              "researchCriterion": {"moreCompletePrimaryFields": more_complete, "bothAmountAndBalanceRecallImprove": numeric_better,
                                    "met": more_complete and numeric_better},
              "intervalEstimates": None, "independentLanguageLabelsAvailable": False,
              "activeModelChanged": False, "productionIntegrated": False, "promotionAllowed": False, "reservedMerchantTestInferred": False,
              "limits": ["Assistant-corrected synthetic labels and bounded grouping proxies are not independent truth.",
                         "Already-valid messages and supplied tokenization; not an end-to-end transaction result.",
                         "Single fixed trial; no hyperparameter/feature search or validation augmentation.",
                         "A research improvement does not establish deployment readiness or independent Arabic generalization."]}
    report_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if model_path.read_text(encoding="utf-8") != model_text or report_path.read_text(encoding="utf-8") != report_text:
            raise ValueError("Context BIO report/model is stale")
    else:
        snapshot_report_inputs("bio_context_" + args.run_id, hashes)
        write_immutable(model_path, model_text)
        write_immutable(report_path, report_text)
    print(f"Context BIO: {len(training)} train / {len(validation)} validation / {len(split['quarantinedIds'])} quarantined")
    print(f"Complete primary fields: {result['exactPrimaryFields']['count']}/{len(validation)}; word {old['exactPrimaryFields']['count']}/{len(validation)}; regex {report['regexValues']['exactPrimaryFields']['count']}/{len(validation)}")
    print(f"Exact sequences: {result['exactSequenceAgreement']['count']}/{len(validation)}; invalid IOB2: {result['invalidIobTransitions']}; Python/TS features and predictions agree; no promotion")


if __name__ == "__main__":
    main()
