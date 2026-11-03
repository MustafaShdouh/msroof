"""Compare the bounded paired-movement repair with source-and-grammar snapshots."""
import argparse
from collections import Counter
import json
import re
import subprocess

from src.python.engine import MasroofEngine
from src.python.ownership_context import assess_with_ownership
from tools.contracts.validate_ownership_context import validate_response
from tools.contracts.validate_transaction_behavior import validate_result
from tools.node_runtime import node_executable
from training.corpus_io import sha256, snapshot_report_inputs, write_immutable
from training.evaluation.detailed import ROOT, load
from training.evaluation.behavior import canonical_result, differences
from training.evaluation.ownership import BASELINE, PAIRED_CONTROLS, baseline_assessor, evaluate as evaluate_ownership

ARABIC_CONTROLS = "tests/fixtures/arabic_message_semantics_cases.json"


def evaluate_pairs():
    engine, old_assess = MasroofEngine(), baseline_assessor()
    old_engine = old_assess.baseline_engine

    def before(input_value, override=None):
        return old_assess(input_value, lambda body, direction: old_engine.extract_entities(body, direction, categorize=False),
                          old_engine.parse_number, lambda text: old_engine._score_tokens(old_engine.tokenize(old_engine.preprocess(text)))[0] >= .70,
                          override)

    definitions = load(PAIRED_CONTROLS)["cases"]
    revisions = load(ARABIC_CONTROLS)["pairedControlRevisions"]
    if not set(revisions) <= {row["id"] for row in definitions}:
        raise ValueError("Unknown versioned paired control revision")
    cases, requests, metadata = [], [], {}
    for row in definitions:
        for script, digits in (("latin", "0123456789"), ("arabic", "٠١٢٣٤٥٦٧٨٩"), ("persian", "۰۱۲۳۴۵۶۷۸۹")):
            key = row["id"] + ":" + script
            text = row["text"].translate(str.maketrans("0123456789", digits))
            cases.append({"id": key, "input": {"text": text}})
            metadata[key] = row
            for relation in (None, "own_accounts", "other_person", "unknown"):
                request = {"ownerScopeId": "paired-development-owner", "messageId": key, "message": {"text": text}}
                if relation is not None:
                    request["ownershipContext"] = {"schemaVersion": "1.0.0", "ownerScopeId": request["ownerScopeId"],
                                                   "messageId": key, "text": text, "evidence": "user_confirmed", "relationship": relation}
                requests.append({"id": key + ":" + (relation or "absent"), "request": request})
    process = subprocess.run([node_executable(), str(ROOT / "tools/evaluation/probe_detailed.ts")],
                             input=json.dumps({"cases": cases, "ownershipCases": requests}),
                             capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if process.returncode:
        raise ValueError(process.stderr)
    outputs = json.loads(process.stdout)
    predictions, changes, bodies, legacy_changes, retained_inclusions = {}, {}, {}, {}, {}
    for case, other in zip(cases, outputs["rows"], strict=True):
        row = metadata[case["id"]]
        result, prior = engine.predict_detailed(case["input"]), before(case["input"])
        validate_result(result)
        if not result == other["typescript"] == other["browser"]:
            raise ValueError("Paired body parity failed: " + case["id"])
        legacy = canonical_result(engine.predict("", case["input"]["text"]))
        old_legacy = canonical_result(old_engine.predict("", case["input"]["text"]))
        if not legacy == other["legacyTypescript"] == other["legacyBrowser"]:
            raise ValueError("Paired legacy parity failed: " + case["id"])
        legacy_fields = differences(old_legacy, legacy)
        if legacy_fields:
            if legacy_fields != ["data.merchantOrParty"] or legacy["data"]["merchantOrParty"] is not None:
                raise ValueError("Unexpected legacy change: " + case["id"])
            legacy_changes[case["id"]] = {"before": old_legacy["data"]["merchantOrParty"], "after": None}
        if row["recognized"]:
            expected = {"transactionStatus": "completed", "trackingDecision": "review", "direction": "uncertain",
                        "transferRelationship": "unknown", "amount": 7.333, "currency": "JOD",
                        "expenseCategory": None, "categoryStatus": "not_applicable", **row["expect"]}
            if any(result[key] != value for key, value in expected.items()):
                raise ValueError("Paired evidence expectation failed: " + case["id"])
            # This change supplies event structure only; monetary/completion facts stay intact.
            if any(result[key] != prior[key] for key in ("transactionStatus", "amount", "currency", "currencyResolution")):
                raise ValueError("Paired recognition changed independent evidence: " + case["id"])
        elif row["id"] in revisions:
            if result != {**prior, **revisions[row["id"]]}:
                raise ValueError("Arabic paired revision differs from its explicit field changes: " + case["id"])
        elif result != prior or result["transferRelationship"] not in ("not_transfer", "not_applicable"):
            raise ValueError("Negative paired control changed or recognized: " + case["id"])
        elif result["trackingDecision"] == "include":
            # Rejecting a new ownership path does not repair unrelated, pre-existing
            # direction/completion gaps. Keep these visible rather than calling them passes in accuracy.
            retained_inclusions[case["id"]] = result
        bodies[case["id"]] = result
        fields = {key: {"before": prior[key], "after": result[key]} for key in prior if prior[key] != result[key]}
        if fields:
            changes[case["id"]] = fields
    statuses = Counter()
    for case, other in zip(requests, outputs["ownershipRows"], strict=True):
        request = case["request"]
        key = request["messageId"]
        row, body = metadata[key], bodies[key]
        result = engine.predict_with_ownership(request)
        validate_response(result)
        if other["id"] != case["id"] or not result == other["typescript"] == other["browser"]:
            raise ValueError("Paired wrapper parity failed: " + case["id"])
        relation = (request.get("ownershipContext") or {}).get("relationship")
        if not row["recognized"]:
            if row["id"] in revisions:
                status = "absent" if relation is None else "not_applicable"
                reason = "not_provided" if relation is None else "non_transaction" if body["transactionStatus"] == "non_transaction" else "not_a_transfer"
                if result["assessment"] != body or (result["contextStatus"], result["contextReason"]) != (status, reason):
                    raise ValueError("Ownership promoted a revised Arabic non-transfer: " + case["id"])
            elif result != assess_with_ownership(request, before):
                raise ValueError("Negative context result changed: " + case["id"])
        elif relation in (None, "unknown"):
            if result["assessment"] != body or result["contextStatus"] != ("absent" if relation is None else "unresolved"):
                raise ValueError("Unconfirmed paired evidence changed: " + case["id"])
        elif relation == "own_accounts":
            if result["contextStatus"] != "applied" or result["assessment"]["trackingDecision"] != "exclude" or result["assessment"]["direction"] != "not_applicable":
                raise ValueError("Confirmed own paired movement failed: " + case["id"])
        else:
            expected_status = "conflict" if body["transferRelationship"] == "own_accounts" else "applied"
            if result["contextStatus"] != expected_status or result["assessment"]["trackingDecision"] != "review" or result["assessment"]["direction"] != "uncertain":
                raise ValueError("Confirmation invented paired direction: " + case["id"])
        predictions[case["id"]] = result
        statuses[result["contextStatus"]] += 1
    return {"authoredTexts": len(definitions), "recognizedTexts": sum(row["recognized"] for row in definitions),
            "digitScripts": 3, "bodyComparisons": len(cases), "wrapperComparisons": len(requests),
            "legacyThreeRuntimeComparisons": len(cases), "contextStatusCounts": dict(statuses),
            "changedBodyFields": changes, "legacyPartyParityRepairs": legacy_changes,
            "retainedMessageOnlyInclusionsAmongUnrecognizedControls": retained_inclusions,
            "predictions": predictions}, outputs["bundleSources"]


def evaluate():
    pairs, sources = evaluate_pairs()
    ownership = evaluate_ownership()  # Requires exact equality on all389 old no-context assessments.
    hashes = dict(ownership["inputSha256"])
    for path in (*sources, ARABIC_CONTROLS, "training/evaluation/paired.py", "tests/python/test_paired_movement.py", "tools/browser/presets.json"):
        hashes[path] = sha256(ROOT / path)
    return {"version": "1.0.0", "scope": "Authored paired-movement conformance; exposed development comparison, not independent accuracy",
            "inputSha256": hashes, "baselineReport": BASELINE, "modelFitted": False, "modelPromoted": False,
            "reservedMerchantTestInferred": False, "legacyCallerMigrated": False,
            "pairedMovement": pairs, "ownership": {k: v for k, v in ownership.items() if k != "inputSha256"},
            "versionedPairedControlRevisions": load(ARABIC_CONTROLS)["pairedControlRevisions"],
            "versionedOwnershipControlRevisions": load(PAIRED_CONTROLS)["ownershipControlOverrides"]}


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
            raise ValueError("Paired report missing or stale")
    else:
        snapshot_report_inputs("paired_" + args.run_id, report["inputSha256"])
        write_immutable(path, content)
    print(json.dumps({key: report["pairedMovement"][key] for key in ("authoredTexts", "recognizedTexts", "bodyComparisons", "wrapperComparisons")}, indent=2))


if __name__ == "__main__":
    main()
