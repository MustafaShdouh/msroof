"""Measure Slice1 detailed contract behavior without changing the legacy path."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.python.verify_engine import MasroofEngine
from tools.contracts.validate_transaction_behavior import validate_result
from training.corpus_io import FIXTURES, sha256, snapshot_report_inputs, write_immutable
from training.evaluate_behavior import canonical_result


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def differences(expected, actual):
    return [key for key, value in expected.items()
            if (set(value) != set(actual[key]) if key == "reasonCodes" else value != actual[key])]


def evaluate():
    policy_path = "tests/fixtures/transaction_behavior_cases.json"
    controls_path = "tests/fixtures/detailed_assessment_cases.json"
    auth_path = "tests/fixtures/authorization_request_cases.json"
    policy, controls, auth = [load(path)["cases"] for path in (policy_path, controls_path, auth_path)]
    regressions, fixture_paths = [], []
    for name in ("test_suite_cases.json", "qa_adversarial_cases.json"):
        path = (FIXTURES / name).relative_to(ROOT).as_posix()
        fixture_paths.append(path)
        regressions += load(path)["testCases"]
    cases = [{"id": "policy:" + c["id"], "input": c["input"]} for c in policy]
    cases += [{"id": "control:" + c["id"], "input": c["input"]} for c in controls]
    cases += [{"id": "authorization:" + c["id"], "input": {"text": c["body"]}} for c in auth]
    cases += [{"id": "regression:" + c["id"], "input": {"sender": c["sender"], "text": c["body"]}} for c in regressions]
    p = subprocess.run([r"C:\Program Files\nodejs\node.exe", str(ROOT / "tools/evaluation/probe_detailed.ts")],
                       input=json.dumps({"cases": cases}), capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if p.returncode:
        raise ValueError(p.stderr)
    other = json.loads(p.stdout)
    if len(other["rows"]) != len(cases):
        raise ValueError("Detailed probe dropped records")
    engine, predictions, legacy = MasroofEngine(), {}, {}
    for case, output in zip(cases, other["rows"]):
        if output["id"] != case["id"]:
            raise ValueError("Detailed probe reordered records")
        result = engine.predict_detailed(case["input"])
        validate_result(result)
        prior = canonical_result(engine.predict(case["input"].get("sender") or "", case["input"]["text"], case["input"].get("isContact", False)))
        if not (result == output["typescript"] == output["browser"] and prior == output["legacyTypescript"] == output["legacyBrowser"]):
            raise ValueError("Detailed or legacy runtime parity mismatch: " + case["id"])
        predictions[case["id"]], legacy[case["id"]] = result, prior
    policy_diffs = [{"caseId": c["id"], "fields": differences(c["expected"], predictions["policy:" + c["id"]])} for c in policy]
    policy_diffs = [row for row in policy_diffs if row["fields"]]
    control_diffs = [{"caseId": c["id"], "fields": differences(c["expect"], predictions["control:" + c["id"]])} for c in controls]
    control_diffs = [row for row in control_diffs if row["fields"]]
    auth_failures = []
    for c in auth:
        result = predictions["authorization:" + c["id"]]
        if (c["request"] and (result["transactionStatus"] != "non_transaction" or result["trackingDecision"] != "exclude")) or (c.get("accepted") and result["trackingDecision"] != "include"):
            auth_failures.append(c["id"])
    compatibility = []
    counts, legacy_counts = Counter(), Counter()
    legacy_misses = []
    field_changes = []
    fields = {"amount": "amount", "currency": "currency", "direction": "direction", "merchantOrCounterparty": "merchantOrParty"}
    for case in regressions:
        key = "regression:" + case["id"]
        result, prior = predictions[key], legacy[key]
        counts[result["trackingDecision"]] += 1
        legacy_counts[str(prior["isValidTransaction"])] += 1
        expected_included = case.get("isTransaction", case.get("isValidTransaction"))
        # Frozen fixture classification lives in its expected transaction flag.
        if expected_included is None:
            expected_included = case["expected"]["isValidTransaction"]
        if prior["isValidTransaction"] != expected_included:
            legacy_misses.append(case["id"])
        if prior["isValidTransaction"] != (result["trackingDecision"] == "include"):
            compatibility.append({"caseId": case["id"], "legacyIncluded": prior["isValidTransaction"],
                                  "detailedDecision": result["trackingDecision"], "transactionStatus": result["transactionStatus"], "reasonCodes": result["reasonCodes"]})
        if prior["data"] and result["trackingDecision"] == "include":
            prior_data = dict(prior["data"])
            prior_data["direction"] = {"INCOMING": "incoming", "OUTGOING": "outgoing"}[prior_data["direction"]]
            changed = [new for new, old in fields.items() if result[new] != prior_data[old]]
            if changed: field_changes.append({"caseId": case["id"], "fields": changed})
    evidence = [policy_path, controls_path, auth_path, *fixture_paths, "data/models/masroof_model.json", "config/contracts/transaction_behavior.json",
                "src/python/verify_engine.py", "src/python/detailed_assessment.py", "src/python/entity_text.py", "src/python/preprocessing.py",
                "src/python/authorization_request.py", "src/python/service_notice.py", "src/python/legacy_transaction_model.py",
                "tools/evaluation/probe_detailed.ts", "tools/browser/tester.html", "tools/browser/build_tester_ui.py", "tools/browser/bundle_engine.mjs",
                "tools/contracts/validate_transaction_behavior.py", "training/corpus_io.py", "training/evaluate_behavior.py", "training/evaluate_detailed.py"]
    evidence += list(other["bundleSources"])
    hashes = {path: sha256(ROOT / path) for path in dict.fromkeys(evidence)}
    return {"version": "1.0.0", "scope": "Approved Slice1 structural assessment; exposed development diagnostics, not independent accuracy",
            "inputSha256": hashes, "modelFitted": False, "modelPromoted": False, "reservedMerchantTestInferred": False,
            "legacyCallerMigrated": False, "contractValidResults": len(cases), "detailedThreeRuntimeParity": len(cases), "legacyThreeRuntimeParity": len(cases),
            "policy": {"caseCount": len(policy), "trackingMatches": sum(predictions["policy:" + c["id"]]["trackingDecision"] == c["expected"]["trackingDecision"] for c in policy),
                       "exactAllFields": len(policy) - len(policy_diffs), "disagreements": policy_diffs,
                       "annotationIssue": "completed_missing_amount has no currency token; explicit in frozen annotation, default_missing from evidence"},
            "contextualControls": {"caseCount": len(controls), "matchingExpectedFields": len(controls) - len(control_diffs), "disagreements": control_diffs},
            "authorizationControls": {"caseCount": len(auth), "failures": auth_failures},
            "frozenCompatibility": {"caseCount": len(regressions), "legacyIncluded": legacy_counts["True"], "legacyExcluded": legacy_counts["False"],
                                    "legacyClassificationDisagreements": legacy_misses, "detailedDecisionCounts": dict(counts),
                                    "changedIncludeProjection": compatibility, "includedFieldChanges": field_changes,
                                    "meaning": "Changes against legacy behavior, not correctness adjudications or label edits; category vocabularies not mapped"},
            "nextGate": "Owner reviews compatibility differences before Slice2 caller migration; deployment thresholds and final evaluation remain unapproved"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_]{1,40}", args.run_id): parser.error("Invalid run ID")
    report = evaluate()
    output = ROOT / f"data/reports/behavior/{args.run_id}.json"
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != content: raise ValueError("Detailed report missing or stale")
    else:
        snapshot_report_inputs("detailed_" + args.run_id, report["inputSha256"])
        write_immutable(output, content)
    print(json.dumps({"policy": report["policy"], "contextualControls": report["contextualControls"],
                      "canonicalParityCases": report["detailedThreeRuntimeParity"],
                      "frozenDetailedDecisions": report["frozenCompatibility"]["detailedDecisionCounts"],
                      "legacyClassificationDisagreements": len(report["frozenCompatibility"]["legacyClassificationDisagreements"]),
                      "changedIncludeProjection": len(report["frozenCompatibility"]["changedIncludeProjection"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
