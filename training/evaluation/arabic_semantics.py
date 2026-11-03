"""Measure Arabic completion/direction repairs without fitting or caller migration."""
import argparse
from collections import Counter
import json
import re
import subprocess

from src.python.engine import MasroofEngine
from tools.contracts.validate_transaction_behavior import validate_result
from tools.contracts.validate_ownership_context import validate_response
from tools.node_runtime import node_executable
from training.corpus_io import sha256, snapshot_report_inputs, write_immutable
from training.evaluation.behavior import canonical_result
from training.evaluation.detailed import ROOT, load
from training.evaluation.ownership import baseline_assessor
from training.evaluation.paired import ARABIC_CONTROLS, evaluate as evaluate_paired


def evaluate_semantics():
    fixture = load(ARABIC_CONTROLS)
    definitions = fixture["cases"]
    old = baseline_assessor(fixture["baselineReport"])
    old_engine, engine = old.baseline_engine, MasroofEngine()
    cases, metadata, requests = [], {}, []
    for row in definitions:
        for script, digits in (("latin", "0123456789"), ("arabic", "٠١٢٣٤٥٦٧٨٩"), ("persian", "۰۱۲۳۴۵۶۷۸۹")):
            key = row["id"] + ":" + script
            text = row["text"].translate(str.maketrans("0123456789", digits))
            cases.append({"id": key, "input": {"text": text}})
            metadata[key] = row
            for relationship in (None, "own_accounts", "other_person", "unknown"):
                request = {"ownerScopeId": "arabic-development-owner", "messageId": key, "message": {"text": text}}
                if relationship is not None:
                    request["ownershipContext"] = {"schemaVersion": "1.0.0", "ownerScopeId": request["ownerScopeId"],
                                                   "messageId": key, "text": text, "evidence": "user_confirmed", "relationship": relationship}
                requests.append({"id": key + ":" + (relationship or "absent"), "request": request})
    process = subprocess.run([node_executable(), str(ROOT / "tools/evaluation/probe_detailed.ts")],
                             input=json.dumps({"cases": cases, "ownershipCases": requests}),
                             capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if process.returncode:
        raise ValueError(process.stderr)
    outputs = json.loads(process.stdout)
    bodies, changes, predictions, decisions, fixed_inclusions = {}, {}, {}, Counter(), []
    for case, other in zip(cases, outputs["rows"], strict=True):
        result = engine.predict_detailed(case["input"])
        prior = old(case["input"], lambda body, direction: old_engine.extract_entities(body, direction, categorize=False),
                    old_engine.parse_number, lambda text: old_engine._score_tokens(old_engine.tokenize(old_engine.preprocess(text)))[0] >= .70)
        validate_result(result)
        if other["id"] != case["id"] or not result == other["typescript"] == other["browser"]:
            raise ValueError("Arabic body parity failed: " + case["id"])
        if any(result[key] != value for key, value in metadata[case["id"]]["expect"].items()):
            raise ValueError("Arabic semantic expectation failed: " + case["id"])
        legacy = canonical_result(engine.predict("", case["input"]["text"]))
        if not legacy == canonical_result(old_engine.predict("", case["input"]["text"])) == other["legacyTypescript"] == other["legacyBrowser"]:
            raise ValueError("Arabic repair changed legacy behavior/parity: " + case["id"])
        fields = {key: {"before": prior[key], "after": result[key]} for key in prior if prior[key] != result[key]}
        if fields:
            changes[case["id"]] = fields
        if prior["trackingDecision"] == "include" and result["trackingDecision"] != "include":
            fixed_inclusions.append(case["id"])
        bodies[case["id"]] = result
        decisions[result["trackingDecision"]] += 1
    for case, other in zip(requests, outputs["ownershipRows"], strict=True):
        result = engine.predict_with_ownership(case["request"])
        validate_response(result)
        if other["id"] != case["id"] or not result == other["typescript"] == other["browser"]:
            raise ValueError("Arabic wrapper parity failed: " + case["id"])
        # These controls describe credits, debits, conflicts or hypothetical events,
        # not an established transfer. Confirmation cannot manufacture a transfer.
        context = case["request"].get("ownershipContext")
        body = bodies[case["request"]["messageId"]]
        expected = ("absent", "not_provided") if context is None else ("not_applicable", "non_transaction" if body["transactionStatus"] == "non_transaction" else "not_a_transfer")
        if result["assessment"] != body or (result["contextStatus"], result["contextReason"]) != expected:
            raise ValueError("Context promoted Arabic non-transfer evidence: " + case["id"])
        predictions[case["id"]] = result
    return {"authoredTexts": len(definitions), "digitScripts": 3, "bodyComparisons": len(cases),
            "wrapperComparisons": len(requests), "legacyUnchangedThreeRuntimeComparisons": len(cases),
            "decisionCounts": dict(decisions), "changedBodyFields": changes,
            "previousInclusionsNowExcludedOrReviewed": fixed_inclusions, "predictions": predictions}


def evaluate():
    semantics = evaluate_semantics()
    previous = evaluate_paired()
    if previous["pairedMovement"]["retainedMessageOnlyInclusionsAmongUnrecognizedControls"]:
        raise ValueError("A known paired-control inclusion remains unresolved")
    inputs = dict(previous["inputSha256"])
    for path in (load(ARABIC_CONTROLS)["baselineReport"], ARABIC_CONTROLS,
                 "training/evaluation/arabic_semantics.py", "tests/python/test_arabic_message_semantics.py"):
        inputs[path] = sha256(ROOT / path)
    return {"version": "1.0.0", "scope": "Authored Arabic semantics/conformance; exposed development, not independent accuracy",
            "inputSha256": inputs, "baselineReport": load(ARABIC_CONTROLS)["baselineReport"],
            "modelFitted": False, "modelPromoted": False, "reservedMerchantTestInferred": False, "legacyCallerMigrated": False,
            "arabicMessageSemantics": semantics, "pairedAndOwnership": {k: v for k, v in previous.items() if k != "inputSha256"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_]{1,40}", args.run_id):
        parser.error("Invalid run ID")
    report = evaluate()
    path = ROOT / f"data/reports/behavior/{args.run_id}.json"
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            raise ValueError("Arabic semantics report missing or stale")
    else:
        snapshot_report_inputs("arabic_semantics_" + args.run_id, report["inputSha256"])
        write_immutable(path, content)
    print(json.dumps({key: report["arabicMessageSemantics"][key] for key in ("authoredTexts", "bodyComparisons", "wrapperComparisons", "decisionCounts")}, indent=2))


if __name__ == "__main__":
    main()
