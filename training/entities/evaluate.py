"""Evaluate the existing word BIO learner on corrected, proxy-isolated folds."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from training.corpus_io import sha256, write_immutable, snapshot_report_inputs
from training.entities.prepare_labels import DATA, SPLIT, REPORT as LABEL_REPORT, POLICY, validate_artifacts
from training.entities.perceptron import train, export_model, TAGS, EPOCHS, SEED
from training.evaluation.behavior import money_equal
from src.python.entity_text import EntityText
from src.python.research.bio_sequence import FlatBioModel, NORMALIZATION_VERSION
from src.python.engine import MasroofEngine
from tools.node_runtime import node_executable

LABELS = ("AMT", "CURR", "MERCHANT", "ACCT", "BAL")


def rate(correct, total):
    return {"count": correct, "total": total, "rate": correct / total if total else None}


def decode_spans(row, predictions):
    """Compare physical entity intervals; report malformed IOB2 separately."""
    if len(predictions) != len(row["tokenOffsets"]) or any(type(tag) is not int or not 0 <= tag < len(TAGS) for tag in predictions):
        raise ValueError("BIO prediction length or tag index is invalid")
    entities, active, start, invalid = [], None, 0, 0
    previous_end = 0
    for index, tag_index in enumerate(predictions):
        tag = TAGS[tag_index]
        prefix, label = tag.split("-", 1) if tag != "O" else ("O", None)
        if active is not None and (prefix != "I" or label != active):
            entities.append((active, start, previous_end))
            active = None
        if prefix == "I" and active != label:
            invalid += 1
        if label is not None and active is None:
            active = label
            start = row["tokenOffsets"][index]["start"]
        previous_end = row["tokenOffsets"][index]["end"]
    if active is not None:
        entities.append((active, start, previous_end))
    return entities, invalid


def entity_metrics(tp, fp, fn):
    return {"truePositives": tp, "falsePositives": fp, "falseNegatives": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}


def slot_value(label, text):
    if label in ("AMT", "BAL"):
        try:
            return MasroofEngine.parse_number(text)
        except (TypeError, ValueError):
            return None
    if label == "CURR":
        return MasroofEngine.normalize_currency(EntityText(text).text)
    if label == "ACCT":
        from src.python.preprocessing import normalize_financial_numbers
        return normalize_financial_numbers(text)
    return text


def slots(row, entities):
    values = {}
    for label in LABELS:
        spans = [(start, end) for kind, start, end in entities if kind == label]
        # Multiple candidate primary fields are unresolved, even if equal.
        values[label] = {"count": len(spans), "value": slot_value(label, row["text"][spans[0][0]:spans[0][1]]) if len(spans) == 1 else None}
    return values


def same_slot(label, expected, actual):
    if expected["count"] != actual["count"]:
        return False
    if expected["count"] == 0:
        return True
    if expected["count"] != 1 or actual["value"] is None:
        return False
    if label in ("AMT", "BAL"):
        return money_equal(expected["value"], actual["value"])
    return expected["value"] == actual["value"]


def metrics(examples, predictions):
    if len(examples) != len(predictions):
        raise ValueError("Missing or extra BIO predictions")
    counts = {label: Counter() for label in LABELS}
    fields = {label: Counter() for label in LABELS}
    correct_tokens = total_tokens = exact_sequences = exact_slots = malformed = 0
    failures = []
    for row, predicted in zip(examples, predictions):
        gold_tags = [TAGS.index(tag) for tag in row["tags"]]
        total_tokens += len(gold_tags)
        correct_tokens += sum(a == b for a, b in zip(gold_tags, predicted))
        exact_sequences += gold_tags == predicted
        raw_spans, invalid = decode_spans(row, predicted)
        malformed += invalid
        gold = Counter((entity["label"], entity["start"], entity["end"]) for entity in row["entities"])
        actual = Counter(raw_spans)
        for label in LABELS:
            counts[label]["tp"] += sum(min(n, gold.get(span, 0)) for span, n in actual.items() if span[0] == label)
            counts[label]["fp"] += sum(n - min(n, gold.get(span, 0)) for span, n in actual.items() if span[0] == label)
            counts[label]["fn"] += sum(n - min(n, actual.get(span, 0)) for span, n in gold.items() if span[0] == label)
        expected_slots, actual_slots = slots(row, gold), slots(row, actual)
        all_fields = True
        for label in LABELS:
            ok = same_slot(label, expected_slots[label], actual_slots[label])
            fields[label]["correct"] += ok
            fields[label]["total"] += 1
            all_fields &= ok
        exact_slots += all_fields
        if not all_fields:
            failures.append(row["id"])
    return {"examples": len(examples), "tokenAgreement": rate(correct_tokens, total_tokens),
            "exactSequenceAgreement": rate(exact_sequences, len(examples)), "exactPrimaryFields": rate(exact_slots, len(examples)),
            "invalidIobTransitions": malformed,
            "perEntityCharacterSpan": {label: entity_metrics(value["tp"], value["fp"], value["fn"]) for label, value in counts.items()},
            "perPrimaryField": {label: rate(value["correct"], value["total"]) for label, value in fields.items()},
            "fieldFailureIds": failures}


def regex_value_metrics(examples):
    engine = MasroofEngine()
    counts = {label: Counter() for label in LABELS}
    exact = 0
    mapping = {"AMT": "amount", "CURR": "currency", "MERCHANT": "merchantOrParty", "ACCT": "accountMask", "BAL": "balance"}
    for row in examples:
        result = engine.predict("", row["text"])
        data = result.get("data") or {}
        expected = slots(row, [(entity["label"], entity["start"], entity["end"]) for entity in row["entities"]])
        all_fields = True
        for label, field in mapping.items():
            value = data.get(field)
            actual = {"count": int(value is not None), "value": value}
            ok = result["isValidTransaction"] and same_slot(label, expected[label], actual)
            counts[label]["correct"] += ok
            counts[label]["total"] += 1
            all_fields &= ok
        exact += all_fields
    return {"exactPrimaryFields": rate(exact, len(examples)),
            "perField": {label: rate(value["correct"], value["total"]) for label, value in counts.items()},
            "characterSpansScorable": False, "reason": "Legacy regex API returns values, not source intervals"}


def prepare_evaluation():
    artifact = json.loads(DATA.read_text(encoding="utf-8"))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    label_report = json.loads(LABEL_REPORT.read_text(encoding="utf-8"))
    for relative, expected in label_report["artifactSha256"].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError("Frozen BIO annotation/split bytes changed")
    if split["status"] != "prepared_development_only" or split["datasetSha256"] != sha256(DATA):
        raise ValueError("BIO split missing or mismatched")
    validate_artifacts(artifact, split)
    by_id = {row["id"]: row for row in artifact["examples"]}
    return [by_id[key] for key in split["trainIds"]], [by_id[key] for key in split["validationIds"]], split


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_]{1,40}", args.run_id):
        parser.error("Invalid run ID")
    training, validation, split = prepare_evaluation()
    model_path = ROOT / f"data/models/bio_{args.run_id}_candidate.json"
    report_path = ROOT / f"data/reports/bio/{args.run_id}_evaluation.json"
    if args.check:
        model = json.loads(model_path.read_text(encoding="utf-8"))
    else:
        if model_path.exists() or report_path.exists():
            raise ValueError("Research outputs exist; choose a new run ID or --check")
        emission, transition = train(training)
        model = export_model(training, emission, transition)
        model["researchSource"] = {"datasetSha256": sha256(DATA), "splitSha256": sha256(SPLIT),
                                   "annotationVersion": "2.0.0", "normalizationVersion": NORMALIZATION_VERSION,
                                   "runtimeScoreDtype": "float32", "scope": "Synthetic, assistant-corrected proxy-grouped development only"}
    if model["researchSource"]["datasetSha256"] != sha256(DATA) or model["researchSource"]["splitSha256"] != sha256(SPLIT):
        raise ValueError("BIO model identifies a different dataset/split")
    runtime = FlatBioModel(model)
    predictions = [runtime.predict(row["tokens"]) for row in validation]
    process = subprocess.run([node_executable(), str(ROOT / "tools/evaluation/probe_bio_model.ts")],
                             input=json.dumps({"model": model, "examples": [row["tokens"] for row in validation]}),
                             capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if process.returncode or json.loads(process.stdout) != predictions:
        raise ValueError("Python/TS BIO prediction mismatch: " + process.stderr)
    sources = [DATA, SPLIT, LABEL_REPORT, POLICY, ROOT / "training/entities/perceptron.py", ROOT / "training/entities/prepare_labels.py",
               ROOT / "training/evaluation/behavior.py", ROOT / "data/models/masroof_model.json",
               ROOT / "training/corpus_io.py", ROOT / "src/python/research/bio_sequence.py", ROOT / "src/typescript/research/BioNormalization.ts",
               ROOT / "src/typescript/MasroofEngine.ts", ROOT / "src/python/engine.py", ROOT / "src/python/entity_text.py",
               ROOT / "src/python/preprocessing.py", ROOT / "src/python/legacy_transaction_model.py", ROOT / "src/python/service_notice.py",
               ROOT / "config/contracts/service_notice.json", ROOT / "src/python/authorization_request.py",
               ROOT / "config/contracts/authorization_request.json", ROOT / "tools/evaluation/probe_bio_model.ts", Path(__file__)]
    hashes = {path.relative_to(ROOT).as_posix(): sha256(path) for path in sources}
    result = metrics(validation, predictions)
    slices = {}
    for name, predicate in (("arabic_script_present", lambda text: bool(re.search(r"[\u0621-\u064a]", text))),
                            ("no_arabic_script", lambda text: not re.search(r"[\u0621-\u064a]", text))):
        selected = [(row, prediction) for row, prediction in zip(validation, predictions) if predicate(row["text"])]
        slices[name] = metrics([row for row, _ in selected], [prediction for _, prediction in selected])
    report = {"version": "2.0.0", "scope": "Existing word learner on corrected synthetic proxy-grouped development; not independent accuracy",
              "inputSha256": hashes, "candidateModelSha256": hashlib.sha256(json.dumps(model, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(),
              "trainCount": len(training), "validationCount": len(validation), "quarantineCount": len(split["quarantinedIds"]),
              "epochs": EPOCHS, "seed": SEED, "modelArchitectureChanged": False,
              "predictionParity": {"pythonTypeScript": True, "count": len(validation), "dtype": "float32 per accumulation"},
              "bio": result, "regexValues": regex_value_metrics(validation), "scriptSlices": slices,
              "independentLanguageLabelsAvailable": False, "intervalEstimates": None,
              "spanDecoder": "Character intervals exact; orphan I tags start an interval and are separately counted as invalid IOB2",
              "promotionAllowed": False, "reservedMerchantTestInferred": False, "activeModelChanged": False,
              "limits": ["Assistant labels and source/template proxies are not human gold or verified independent families.",
                         "The learner is conditioned on already-valid messages and provided tokenization, not end-to-end transaction detection.",
                         "Numeric token memorization remains possible; no new context/shape architecture was fitted.",
                         "Older BIO metrics use different labels and folds and cannot be used as a direct improvement denominator."]}
    model_text = json.dumps(model, ensure_ascii=False, separators=(',', ':'))
    report_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if model_path.read_text(encoding="utf-8") != model_text or report_path.read_text(encoding="utf-8") != report_text:
            raise ValueError("BIO evaluation missing or stale")
    else:
        snapshot_report_inputs("bio_eval_" + args.run_id, hashes)
        write_immutable(model_path, model_text)
        write_immutable(report_path, report_text)
    print(f"BIO development: {len(training)} train / {len(validation)} validation / {len(split['quarantinedIds'])} quarantined")
    print(f"Exact sequences: {result['exactSequenceAgreement']['count']}/{len(validation)}; exact primary values: {result['exactPrimaryFields']['count']}/{len(validation)}; Python/TS parity verified")
    print(f"Regex exact primary values: {report['regexValues']['exactPrimaryFields']['count']}/{len(validation)}; no promotion")


if __name__ == "__main__":
    main()
