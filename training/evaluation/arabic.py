"""Audit Arabic baseline coverage and diagnostic Unicode formats in both engines.

Derived probes are diagnostic only; they are never category-training examples or
additions to the frozen corpus. No runtime normalization is changed here.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from training.corpus_io import FIXTURES, write_immutable, sha256
from src.python.engine import MasroofEngine
from src.python.preprocessing import PREPROCESSING_CONTRACT_VERSION, preprocess_message, tokenize_features
from tools.node_runtime import node_executable

REPORT = ROOT / "data/reports/arabic_support_sanitized_v1_evaluation.json"
INPUT = ROOT / "data/reports/arabic_support_sanitized_v1_probe_inputs.json"
NODE = Path(node_executable())
ARABIC = re.compile(r"[\u0621-\u064a]")


def load_cases() -> list[dict]:
    cases = []
    for name in ("test_suite_cases.json", "qa_adversarial_cases.json"):
        payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        cases.extend(payload["testCases"] if isinstance(payload, dict) else payload)
    return cases


def summarize(cases: list[dict], results: list[dict]) -> dict:
    classification_correct = 0
    positives = 0
    exact_core = 0
    failures = []
    for case, result in zip(cases, results):
        expected = case["expected"]
        classification_correct += result["isValidTransaction"] == expected["isValidTransaction"]
        if not expected["isValidTransaction"]:
            continue
        positives += 1
        data = result.get("data") or {}
        amount = data.get("amount")
        success = result["isValidTransaction"] and amount is not None and abs(amount - expected["amount"]) < 0.001 and data.get("currency") == expected["currency"] and data.get("type") == expected["type"]
        exact_core += bool(success)
        if not success:
            failures.append({"id": case["id"], "accepted": result["isValidTransaction"], "expectedAmount": expected["amount"], "actualAmount": amount, "expectedType": expected["type"], "actualType": data.get("type")})
    return {"caseCount": len(cases), "classificationCorrect": classification_correct, "validTransactionCount": positives, "amountCurrencyDirectionCorrect": exact_core, "failures": failures}


def main():
    cases = [case for case in load_cases() if ARABIC.search(case["body"])]
    selected = {}
    for case in cases:
        if case["expected"]["isValidTransaction"]:
            selected.setdefault(case["provider"], case)
    examples = list(selected.values())[:8]
    groups = {"frozenArabicText": cases}
    for name, digits, separators in (
        ("arabicIndicDigits", "٠١٢٣٤٥٦٧٨٩", False),
        ("persianDigits", "۰۱۲۳۴۵۶۷۸۹", False),
        ("arabicIndicDigitsAndSeparators", "٠١٢٣٤٥٦٧٨٩", True),
    ):
        transformed = []
        for case in examples:
            body = case["body"].translate(str.maketrans("0123456789", digits))
            if separators:
                body = body.replace(".", "٫").replace(",", "٬")
            transformed.append({**case, "id": name + ":" + case["id"], "body": body})
        groups[name] = transformed
    preprocessing_inputs = ["رقم المرجع ١٢٣٤٥٦٧", "رقم المرجع ۱۲۳۴۵۶۷", "مرجع123456", "تم دفع ١٢٫٥٠ دينار"]
    write_immutable(INPUT, json.dumps({"scope": "diagnostic only; derived from frozen fixtures, not independent training data", "groups": groups, "preprocessingInputs": preprocessing_inputs}, ensure_ascii=False, indent=2) + "\n")
    engine = MasroofEngine()
    python = {name: summarize(group, [engine.predict(case["sender"], case["body"]) for case in group]) for name, group in groups.items()}
    process = subprocess.run([str(NODE), str(ROOT / "tools/evaluation/probe_arabic.ts"), str(INPUT)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    typescript = json.loads(process.stdout)
    preprocessing = []
    for raw, ts_result in zip(preprocessing_inputs, typescript["preprocessing"]):
        normalized = preprocess_message(raw)
        py_result = {"normalized": normalized, "features": tokenize_features(normalized)}
        preprocessing.append({"raw": raw, "python": py_result, "typescript": ts_result, "parity": py_result == ts_result})
    businesses = [json.loads(line) for line in (ROOT / "data/annotations/businesses_200.jsonl").read_text(encoding="utf-8").splitlines()]
    reviews = [json.loads(line) for line in (ROOT / "data/annotations/merchant_reviews.jsonl").read_text(encoding="utf-8").splitlines()]
    report = {
        "version": "1.2.0-sanitized",
        "inputSha256": {str(path.relative_to(ROOT)): sha256(path) for path in [FIXTURES / "test_suite_cases.json", FIXTURES / "qa_adversarial_cases.json", ROOT / "data/models/masroof_model.json", ROOT / "src/python/engine.py", ROOT / "src/typescript/MasroofEngine.ts"]}, "geographicScope": "Jordan", "preprocessingVersion": PREPROCESSING_CONTRACT_VERSION,
        "scope": "Existing Arabic-containing fixture text plus diagnostic digit-format transformations; not independent generalization evidence.",
        "baselineArabicCaseCount": len(cases), "digitProbeSourceProviders": list(selected)[:8],
        "python": python, "typescript": typescript["groups"], "preprocessingParityProbes": preprocessing,
        "categoryCorpus": {"businessCount": len(businesses), "arabicCanonicalNames": sum(bool(ARABIC.search(row["name"])) for row in businesses), "businessesWithArabicNameOrAlias": sum(any(ARABIC.search(name) for name in [row["name"]] + row["aliases"]) for row in businesses), "reviewRecordCount": len(reviews), "approvedArabicMerchantNames": sum(row["status"] == "approved" and row.get("reviewerType", "human") == "human" and row["labelScope"] == "merchant_name" and bool(ARABIC.search(row["name"])) for row in reviews)},
        "nextWork": ["Continue source-verified Arabic alias collection; see categoryCorpus for current coverage, which does not establish category accuracy.", "Prepare independent Jordan-specific Arabic evaluation; hold out entire brands including all Arabic and English aliases.", "Standalone merchant-name candidates are research only; no validated full-taxonomy SMS categorizer or independent Arabic category accuracy is established. See merchant_category_research.json for the separate candidate experiment."]
    }
    write_immutable(REPORT, json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    compact = {
        engine_name: {group_name: {key: value for key, value in metrics.items() if key != "failures"} for group_name, metrics in measurements.items()}
        for engine_name, measurements in (("python", python), ("typescript", typescript["groups"]))
    }
    print(json.dumps({**compact, "categoryCorpus": report["categoryCorpus"], "preprocessingParityFailures": sum(not row["parity"] for row in preprocessing)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
