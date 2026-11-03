"""Measure opt-in ownership controls and equality with the pre-feature assessment."""
import argparse
from collections import Counter
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from src.python.engine import MasroofEngine
from tools.contracts.validate_ownership_context import validate_response
from tools.node_runtime import node_executable
from training.corpus_io import FIXTURES, recorded_source, sha256, snapshot_report_inputs, write_immutable
from training.evaluation.detailed import ROOT, load, evaluate as evaluate_detailed
from training.evaluation.behavior import canonical_result

BASELINE = "data/reports/behavior/ownership_tester_v1.json"
CONTROLS = "tests/fixtures/ownership_context_cases.json"
PAIRED_CONTROLS = "tests/fixtures/paired_movement_cases.json"


def ownership_controls():
    rows = load(CONTROLS)["cases"]
    overrides = load(PAIRED_CONTROLS)["ownershipControlOverrides"]
    if not set(overrides) <= {row["id"] for row in rows}:
        raise ValueError("Unknown versioned ownership control revision")
    return [{**row, **overrides.get(row["id"], {})} for row in rows]


def baseline_assessor(report_path=BASELINE):
    hashes = load(report_path)["inputSha256"]
    # Replay the exact old source AND grammar, never historical source/new grammar.
    for path in ("src/python/preprocessing.py",
                 "src/python/ownership_context.py", "data/models/masroof_model.json",
                 "src/python/authorization_request.py", "src/python/service_notice.py"):
        if sha256(ROOT / path) != hashes[path]:
            raise ValueError("Ownership baseline dependency changed: " + path)
    # Source-view repairs must not leak into this immutable pre-feature baseline.
    view_path = 'src/python/entity_text.py'
    view_namespace = {'__file__': str(ROOT/view_path), '__package__': 'src.python'}
    exec(compile(recorded_source(view_path, hashes[view_path]), str(ROOT/view_path), 'exec'), view_namespace)
    path = "src/python/detailed_assessment.py"
    raw = recorded_source(path, hashes[path])
    with tempfile.TemporaryDirectory(prefix="masroof-assessor-") as directory:
        archive = Path(directory)
        grammar = archive / "config/contracts/transaction_evidence.json"
        grammar.parent.mkdir(parents=True)
        grammar.write_bytes(recorded_source("config/contracts/transaction_evidence.json", hashes["config/contracts/transaction_evidence.json"]))
        namespace = {"__file__": str(archive / path), "__package__": "src.python"}
        exec(compile(raw, str(ROOT / path), "exec"), namespace)
        namespace['EntityText'] = view_namespace['EntityText']
    engine_path = "src/python/engine.py"
    engine_namespace = {"__file__": str(ROOT / engine_path), "__package__": "src.python"}
    exec(compile(recorded_source(engine_path, hashes[engine_path]), str(ROOT / engine_path), "exec"), engine_namespace)
    engine_namespace['EntityText'] = view_namespace['EntityText']
    namespace["assess"].baseline_engine = engine_namespace["MasroofEngine"]()
    return namespace["assess"]


def no_context_cases():
    cases = []
    for name in ("transaction_behavior_cases", "detailed_assessment_cases"):
        cases += [{"id": name + ":" + row["id"], "input": row["input"]}
                  for row in load("tests/fixtures/" + name + ".json")["cases"]]
    cases += [{"id": "auth:" + row["id"], "input": {"text": row["body"]}}
              for row in load("tests/fixtures/authorization_request_cases.json")["cases"]]
    for name in ("test_suite_cases", "qa_adversarial_cases"):
        cases += [{"id": name + ":" + row["id"], "input": {"sender": row["sender"], "text": row["body"]}}
                  for row in load((FIXTURES / (name + ".json")).relative_to(ROOT))["testCases"]]
    return cases


def evaluate():
    engine, old_assess = MasroofEngine(), baseline_assessor()
    controls, cases = ownership_controls(), no_context_cases()
    requests = list(controls)
    for case in cases:
        for mode in ("omitted", "null"):
            request = {"ownerScopeId": "development-owner", "messageId": case["id"], "message": case["input"]}
            if mode == "null":
                request["ownershipContext"] = None
            requests.append({"id": mode + ":" + case["id"], "request": request})
    process = subprocess.run([node_executable(), str(ROOT / "tools/evaluation/probe_detailed.ts")],
                             input=json.dumps({"cases": cases, "ownershipCases": requests}),
                             capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if process.returncode:
        raise ValueError(process.stderr)
    outputs = json.loads(process.stdout)
    baseline_predictions = {}
    for case, other in zip(cases, outputs["rows"], strict=True):
        old_engine = old_assess.baseline_engine
        result = old_assess(case["input"], lambda body, direction: old_engine.extract_entities(body, direction, categorize=False),
                            old_engine.parse_number, lambda text: old_engine._score_tokens(old_engine.tokenize(old_engine.preprocess(text)))[0] >= 0.70)
        if not result == engine.predict_detailed(case["input"]) == other["typescript"] == other["browser"]:
            raise ValueError("Existing assessment changed: " + case["id"])
        sender, contact = case["input"].get("sender") or "", case["input"].get("isContact", False)
        if canonical_result(engine.predict(sender, case["input"]["text"], contact)) != canonical_result(old_engine.predict(sender, case["input"]["text"], contact)):
            raise ValueError("Existing legacy assessment changed: " + case["id"])
        baseline_predictions[case["id"]] = result
    predictions, statuses = {}, Counter()
    for case, other in zip(requests, outputs["ownershipRows"], strict=True):
        result = engine.predict_with_ownership(case["request"])
        validate_response(result)
        if other["id"] != case["id"] or not result == other["typescript"] == other["browser"]:
            raise ValueError("Ownership runtime parity failure: " + case["id"])
        if "expect" in case:
            if (result["contextStatus"], result["contextReason"]) != (case["contextStatus"], case["contextReason"]):
                raise ValueError("Ownership diagnostic mismatch: " + case["id"])
            if any(result["assessment"][key] != value for key, value in case["expect"].items()):
                raise ValueError("Ownership evidence mismatch: " + case["id"])
            if case["sameAsBody"] and result["assessment"] != engine.predict_detailed(case["request"]["message"]):
                raise ValueError("Body assessment unexpectedly changed: " + case["id"])
            predictions[case["id"]] = result
            statuses[result["contextStatus"]] += 1
        else:
            if result["contextStatus"] != "absent" or result["assessment"] != baseline_predictions[case["request"]["messageId"]]:
                raise ValueError("No-context result changed: " + case["id"])
    detailed = evaluate_detailed()
    inputs = dict(detailed["inputSha256"])
    for path in (BASELINE, CONTROLS, PAIRED_CONTROLS, "config/contracts/ownership_context.json", "src/python/ownership_context.py",
                 "tools/contracts/validate_ownership_context.py", "tests/python/test_ownership_context.py",
                 "training/evaluation/ownership.py", "tools/browser/ownership_tester.js",
                 "tests/typescript/test_ownership_tester.ts"):
        inputs[path] = sha256(ROOT / path)
    return {"version": "1.0.0", "scope": "Authored ownership conformance and exposed development parity; not independent accuracy",
            "inputSha256": inputs, "modelFitted": False, "modelPromoted": False,
            "reservedMerchantTestInferred": False, "legacyCallerMigrated": False,
            "ownershipControls": len(controls), "ownershipStatusCounts": dict(statuses),
            "threeRuntimeWrapperComparisons": len(requests), "unchangedBaselineAssessments": len(cases),
            "unchangedLegacyBaselineAssessments": len(cases),
            "unchangedNoContextAssessmentsPerRuntime": 2 * len(cases),
            "baselinePredictionSha256": hashlib.sha256(json.dumps(baseline_predictions, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
            "predictions": predictions, "detailedMeasurement": {key: value for key, value in detailed.items() if key != "inputSha256"}}


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
            raise ValueError("Ownership report missing or stale")
    else:
        snapshot_report_inputs("ownership_" + args.run_id, report["inputSha256"])
        write_immutable(path, content)
    print(json.dumps({key: report[key] for key in ("ownershipControls", "threeRuntimeWrapperComparisons",
                     "unchangedBaselineAssessments", "unchangedNoContextAssessmentsPerRuntime")}, indent=2))


if __name__ == "__main__":
    main()
