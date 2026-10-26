"""Measure current behavior and API gaps without fitting or final-test inference."""
import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training.corpus_io import FIXTURES, sha256, write_immutable, snapshot_report_inputs
from src.python.preprocessing import normalize_financial_numbers
from src.python.verify_engine import MasroofEngine
from tools.contracts.validate_transaction_behavior import load_contract, validate_bundle
from tests.python.validate_test_corpus import validate_baseline

ALIASES = {"merchant_or_party": "merchantOrParty", "account_mask": "accountMask",
           "category_confidence": "categoryConfidence", "original_amount": "originalAmount",
           "original_currency": "originalCurrency", "exchange_rate": "exchangeRate"}
UNSUPPORTED = "unsupported"


def ratio(numerator, denominator):
    return {"correctOrCount": numerator, "total": denominator,
            "rate": numerator / denominator if denominator else None}


def money_equal(a, b):
    if type(a) not in (int, float) or type(b) not in (int, float):
        return False
    try:
        return math.isfinite(a) and math.isfinite(b) and Decimal(str(a)) == Decimal(str(b))
    except (ValueError, InvalidOperation, OverflowError):
        return False


def text_value(value):
    if value is None:
        return None
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", normalize_financial_numbers(str(value)))).strip().casefold()


def currency(value):
    return {"$": "USD", "€": "EUR", "£": "GBP"}.get(value, value)


def canonical_result(value):
    """Remove only validated Python aliases; retain every other output field."""
    result = json.loads(json.dumps(value, allow_nan=False))
    data = result.get("data")
    if isinstance(data, dict):
        for alias, field in ALIASES.items():
            if alias in data:
                if field not in data or data[alias] != data[field]:
                    raise ValueError("Python compatibility alias disagrees with canonical field")
                del data[alias]
    return result


def differences(left, right, prefix=""):
    if isinstance(left, dict) and isinstance(right, dict):
        result = []
        for key in sorted(left.keys() | right.keys()):
            name = prefix + key
            if key not in left or key not in right:
                result.append(name)
            else:
                result.extend(differences(left[key], right[key], name + "."))
        return result
    return [] if left == right else [prefix.rstrip(".")]


def decision(envelope):
    result = envelope.get("result")
    if not isinstance(result, dict) or type(result.get("isValidTransaction")) is not bool:
        return UNSUPPORTED
    # An observable compatibility projection, not a completion-status guess.
    return "include" if result["isValidTransaction"] else "exclude"


def data_for(envelope):
    result = envelope.get("result") or {}
    return (result.get("data") or {}) if decision(envelope) == "include" else {}


def policy_metrics(cases, outputs, categories):
    confusion = {expected: dict.fromkeys(("include", "exclude", "review", UNSUPPORTED), 0)
                 for expected in ("include", "exclude", "review")}
    ordinary = [c for c in cases if c["expected"]["transactionStatus"] == "non_transaction"]
    eligible = [c for c in cases if c["expected"]["trackingDecision"] == "include"]
    own = [c for c in cases if c["expected"]["transferRelationship"] == "own_accounts"]
    p2p = [c for c in eligible if c["expected"]["transferRelationship"] == "other_person"]
    outgoing = [c for c in eligible if c["expected"]["direction"] == "outgoing"]
    accepted = [c for c in eligible if decision(outputs[c["id"]]) == "include"]
    fields = {"trackingDecision": {"correct": 0, "total": len(cases), "unsupported": 0}}
    failures = []
    for case in cases:
        wanted, got = case["expected"], decision(outputs[case["id"]])
        confusion[wanted["trackingDecision"]][got] += 1
        fields["trackingDecision"]["correct"] += got == wanted["trackingDecision"]
        fields["trackingDecision"]["unsupported"] += got == UNSUPPORTED
        if got != wanted["trackingDecision"]:
            failures.append({"caseId": case["id"], "expected": wanted["trackingDecision"], "actual": got})
    def joint(case):
        data = data_for(outputs[case["id"]])
        return money_equal(data.get("amount"), case["expected"]["amount"]) and currency(data.get("currency")) == case["expected"]["currency"]
    def direction_ok(case):
        return {"INCOMING": "incoming", "OUTGOING": "outgoing"}.get(data_for(outputs[case["id"]]).get("direction")) == case["expected"]["direction"]
    def predicted_category(case):
        return data_for(outputs[case["id"]]).get("category")
    claimed = [c for c in outgoing if predicted_category(c) not in (None, "General & Uncategorized")]
    canonical = [c for c in claimed if predicted_category(c) in categories]
    labeled = [c for c in canonical if c["expected"]["categoryStatus"] == "assigned"]
    unsupported_assignments = [c for c in canonical if c["expected"]["categoryStatus"] == "uncertain"]
    default_cases = [c for c in eligible if c["expected"]["currencyResolution"].startswith("default_")]
    return {
        "scope": "Authored conformance probes, not admitted benchmark data or independent accuracy",
        "caseCount": len(cases), "trackingDecisionProjection": "Legacy boolean -> include/exclude; review unavailable",
        "trackingDecisionConfusion": confusion, "trackingFailures": failures,
        "completionStatusConfusion": {status: {UNSUPPORTED: sum(c["expected"]["transactionStatus"] == status for c in cases)}
                                      for status in ("completed", "non_transaction", "uncertain")},
        "unsupportedContractFields": ["contractVersion", "transactionStatus", "reasonCodes", "currencyResolution", "transferRelationship", "categoryStatus"],
        "trackingDecision": fields["trackingDecision"],
        "ordinaryFalseInclusion": ratio(sum(decision(outputs[c["id"]]) == "include" for c in ordinary), len(ordinary)),
        "eligibleMissOrReview": ratio(sum(decision(outputs[c["id"]]) != "include" for c in eligible), len(eligible)),
        "ownAccountLeakage": ratio(sum(decision(outputs[c["id"]]) == "include" for c in own), len(own)),
        "ownAccountExclusions": ratio(sum(decision(outputs[c["id"]]) == "exclude" for c in own), len(own)),
        "p2pCoverage": ratio(sum(decision(outputs[c["id"]]) == "include" for c in p2p), len(p2p)),
        "p2pByDirection": {name: ratio(sum(decision(outputs[c["id"]]) == "include" for c in p2p if c["expected"]["direction"] == name),
                                      sum(c["expected"]["direction"] == name for c in p2p)) for name in ("incoming", "outgoing")},
        "amountCurrencyAllEligible": ratio(sum(joint(c) for c in eligible), len(eligible)),
        "amountCurrencyAcceptedEligible": ratio(sum(joint(c) for c in accepted), len(accepted)),
        "directionAllEligible": ratio(sum(direction_ok(c) for c in eligible), len(eligible)),
        "directionAcceptedEligible": ratio(sum(direction_ok(c) for c in accepted), len(accepted)),
        "defaultCurrencyPolicy": {"caseCount": len(default_cases), "resolutionMarkerScorable": False,
                                  "fallbackValueAgreementOnly": ratio(sum(joint(c) for c in default_cases), len(default_cases))},
        "category": {"eligibleOutgoing": len(outgoing), "legacyClaimedAssignments": len(claimed),
                     "unsupportedTaxonomyAssignments": len(claimed) - len(canonical),
                     "canonicalCoverage": ratio(len(canonical), len(outgoing)),
                     "canonicalAnsweredAgreement": ratio(sum(predicted_category(c) == c["expected"]["expenseCategory"] for c in labeled), len(labeled) + len(unsupported_assignments)),
                     "unsupportedContextAssignments": len(unsupported_assignments),
                     "note": "Legacy taxonomy is not mapped to target categories; unsupported labels are not counted as abstentions"},
        "transferSlices": {relation: {"caseCount": sum(c["expected"]["transferRelationship"] == relation for c in cases),
                                      "trackingCorrect": sum(c["expected"]["transferRelationship"] == relation and decision(outputs[c["id"]]) == c["expected"]["trackingDecision"] for c in cases)}
                           for relation in ("not_transfer", "own_accounts", "other_person", "unknown", "not_applicable")},
    }


def regression_metrics(cases, outputs):
    counts = Counter()
    field_counts = {name: Counter() for name in ("type", "amount", "currency", "merchantOrParty", "accountMask", "balance")}
    failures = []
    for case in cases:
        expected, output = case["expected"], outputs[case["id"]]
        include = decision(output) == "include"
        wanted = expected["isValidTransaction"]
        counts["cases"] += 1
        counts["classificationCorrect"] += include == wanted and decision(output) != UNSUPPORTED
        counts["runtimeErrors"] += "error" in output
        counts["falsePositive"] += include and not wanted
        counts["falseNegative"] += not include and wanted
        if include != wanted:
            failures.append({"caseId": case["id"], "field": "trackingDecision"})
        if not wanted:
            continue
        data = data_for(output)
        for name, metric in field_counts.items():
            if expected.get(name) is None:
                continue  # Legacy null means not annotated, not verified absence.
            metric["eligible"] += 1
            metric["accepted"] += include
            a, b = expected[name], data.get(name)
            if name in ("amount", "balance"):
                ok = money_equal(a, b)
            elif name == "currency":
                ok = currency(a) == currency(b)
            else:
                ok = text_value(a) == text_value(b)
            metric["exact"] += ok
            metric["exactAccepted"] += ok and include
            if not ok:
                failures.append({"caseId": case["id"], "field": name})
    return {**dict(counts), "fieldValues": {key: {"allEligible": ratio(value["exact"], value["eligible"]),
                                                         "acceptedEligible": ratio(value["exactAccepted"], value["accepted"])} for key, value in field_counts.items()},
            "failures": failures, "comparison": "Decimal-exact numbers and normalized whole strings; no substring acceptance or money tolerance",
            "exactCharacterSpans": {"scorable": False, "reason": "No independently reviewed span annotations available"}}


def load_inputs():
    errors = validate_baseline()
    if errors:
        raise ValueError(errors)
    contract = load_contract()
    bundle = json.loads((ROOT / "tests/fixtures/transaction_behavior_cases.json").read_text(encoding="utf-8"))
    validate_bundle(bundle, contract)
    regression = []
    for name in ("test_suite_cases.json", "qa_adversarial_cases.json"):
        regression.extend(json.loads((FIXTURES / name).read_text(encoding="utf-8"))["testCases"])
    cases = [{"id": c["id"], "input": {"sender": c["sender"], "text": c["body"]}} for c in regression] + bundle["cases"]
    guards = json.loads((ROOT / "tests/fixtures/service_notice_cases.json").read_text(encoding="utf-8"))["cases"]
    cases += [{"id": "guard:" + c["id"], "input": {"sender": "SERVICE", "text": c["body"]}} for c in guards]
    presets = json.loads((ROOT / "tools/browser/presets.json").read_text(encoding="utf-8"))["presets"]
    cases += [{"id": "preset:" + key, "input": {"sender": c["sender"], "text": c["body"]}} for key, c in presets.items()]
    entities = json.loads((ROOT / "tests/fixtures/entity_text_cases.json").read_text(encoding="utf-8"))["cases"]
    cases += [{"id": "name:" + c["id"], "input": {"sender": "SERVICE", "text": c["text"]}} for c in entities]
    return contract, bundle, regression, cases


def evaluate():
    contract, bundle, regression, cases = load_inputs()
    engine = MasroofEngine()
    python = []
    for case in cases:
        item = case["input"]
        try:
            envelope = {"result": canonical_result(engine.predict(item.get("sender") or "", item["text"], item.get("isContact", False)))}
        except Exception as error:
            envelope = {"error": type(error).__name__}
        python.append({"id": case["id"], **envelope})
    policies = [{"id": c["reviewId"], "text": c["text"]} for c in bundle["reviewedCategoryPolicies"]]
    process = subprocess.run([r"C:\Program Files\nodejs\node.exe", str(ROOT / "tools/evaluation/probe_runtime.ts")],
                             input=json.dumps({"cases": cases, "categoryProbes": policies}), capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if process.returncode:
        raise ValueError("Runtime probe failed: " + process.stderr.strip())
    other = json.loads(process.stdout)
    runtimes = {"python": python, "typescript": other["typescript"], "browser": other["browser"]}
    summaries = {}
    for name, rows in runtimes.items():
        outputs = {row["id"]: {k: v for k, v in row.items() if k != "id"} for row in rows}
        summaries[name] = {"conformanceProbes": policy_metrics(bundle["cases"], outputs, contract["categories"]),
                           "languageSlices": {language: policy_metrics([c for c in bundle["cases"] if c["language"] == language], outputs, contract["categories"]) for language in ("english", "arabic", "mixed")},
                           "frozenRegressionStrict": regression_metrics(regression, outputs)}
    parity = {}
    reference = {row["id"]: {k: v for k, v in row.items() if k != "id"} for row in python}
    for name in ("typescript", "browser"):
        mismatches = []
        for row in runtimes[name]:
            fields = differences(reference[row["id"]], {k: v for k, v in row.items() if k != "id"})
            if fields:
                mismatches.append({"caseId": row["id"], "fields": fields})
        parity[name + "VsPython"] = {"caseCount": len(cases), "identical": len(cases) - len(mismatches), "mismatches": mismatches}
    category_probes = []
    for case, other_case in zip(bundle["reviewedCategoryPolicies"], other["categories"]):
        values = {"python": {"result": engine.classify_category(None, case["text"])},
                  "typescript": other_case["typescript"], "browser": other_case["browser"]}
        category_probes.append({"reviewId": case["reviewId"], "scope": case["scope"],
                                "expectedCategory": case["expectedCategory"], "expectedStatus": case["categoryStatus"],
                                "componentPredictions": values})
    evidence = ["config/contracts/transaction_behavior.json", "tests/fixtures/transaction_behavior_cases.json",
                "tests/fixtures/sanitized_v1/test_suite_cases.json", "tests/fixtures/sanitized_v1/qa_adversarial_cases.json",
                "tests/fixtures/service_notice_cases.json", "data/models/masroof_model.json", "tools/browser/presets.json",
                "src/python/verify_engine.py", "src/python/preprocessing.py", "src/python/service_notice.py",
                "src/python/legacy_transaction_model.py", "src/typescript/LegacyTransactionModel.ts", "tools/browser/bundle_engine.mjs",
                "src/python/entity_text.py", "src/typescript/EntityText.ts", "config/contracts/entity_text.json", "tests/fixtures/entity_text_cases.json",
                "src/typescript/MasroofEngine.ts", "src/typescript/Preprocessing.ts", "src/typescript/ServiceNotice.ts",
                "config/contracts/service_notice.json", "src/python/authorization_request.py", "src/typescript/AuthorizationRequest.ts",
                "config/contracts/authorization_request.json", "tools/browser/tester.html", "tools/browser/build_tester_ui.py",
                "tools/evaluation/probe_runtime.ts", "training/evaluate_behavior.py"]
    evidence.append("training/corpus_io.py")
    return {"reportVersion": "1.0.0", "scope": "Development behavior/conformance diagnostics only; no independent benchmark accuracy",
            "inputSha256": {path: sha256(ROOT / path) for path in evidence},
            "inputAdapter": "text -> legacy body; absent/null sender -> empty string; contact flag preserved; no sender identity invented",
            "runtimes": summaries, "fullResultParity": parity, "exactHumanCategoryPolicyProbes": category_probes,
            "browserBundleSources": other["bundleSources"], "bundledModelMatchesSource": other["bundledModelMatchesSource"],
            "sourceTemplateSlices": {"verifiedFamiliesAvailableForRegression": False,
                                     "reason": "Legacy provider/category tags are not independently verified source/template family IDs"},
            "uncertaintyIntervals": {"samplingInterval": None, "reason": "Authored and correlated development examples are not independent samples"},
            "releaseDecision": "not_evaluated", "independentFinalEvaluationAvailable": False,
            "modelFitted": False, "modelPromoted": False, "reservedMerchantTestInferred": False}


def readable(report):
    lines = ["# Behavior evaluation", "", report["scope"], "", "| Runtime | Include/exclude projection | Ordinary false inclusions | Eligible misses/reviews | P2P included |", "| --- | --- | --- | --- | --- |"]
    def count(value):
        return f"{value['correctOrCount']}/{value['total']}" if value["total"] else "unmeasurable (0 cases)"
    for name, runtime in report["runtimes"].items():
        p = runtime["conformanceProbes"]
        lines.append(f"| {name} | {p['trackingDecision']['correct']}/{p['caseCount']} | {count(p['ordinaryFalseInclusion'])} | {count(p['eligibleMissOrReview'])} | {count(p['p2pCoverage'])} |")
    lines += ["", "The legacy boolean projection cannot emit review. Completion status, ownership, currency-resolution markers and category-status fields are unsupported; they are not guessed from rejection reasons.", "",
              "Legacy category labels are not silently mapped onto the target 15-category taxonomy. Human category snapshots are component probes for the exact reviewed scenarios only, not new transaction labels.", "",
              "## Complete result parity", ""]
    lines += [f"- {name}: {value['identical']}/{value['caseCount']} identical canonical outputs." for name, value in report["fullResultParity"].items()]
    lines += ["", "Python duplicate aliases are validated then removed; every other field, including reasons, confidence, categories and FX values, is compared. Existing frozen compatibility gates are reported separately from stricter decimal/whole-value checks in the JSON.", "",
              "Exact character spans and independent source/template-family slices are unmeasurable with current truth. Rates on authored/regression data do not establish deployment accuracy; sampling intervals are not claimed for correlated examples.", "",
              "No fitting, promotion, reserved merchant-test inference or final release evaluation occurred.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_]{1,40}", args.run_id):
        parser.error("Invalid run ID")
    report = evaluate()
    if not args.check:
        snapshot_report_inputs("behavior_" + args.run_id, report["inputSha256"])
    outputs = {ROOT / f"data/reports/behavior/{args.run_id}.json": json.dumps(report, ensure_ascii=False, indent=2) + "\n",
               ROOT / f"data/reports/behavior/{args.run_id}.md": readable(report)}
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise ValueError("Behavior report missing or stale: " + str(path))
        else:
            write_immutable(path, content)
    print(readable(report))


if __name__ == "__main__":
    main()
