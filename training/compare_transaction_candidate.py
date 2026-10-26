"""Offline comparison with the same runtime guards/extraction; never promotion."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training.corpus_io import DATASET, SPLIT, FIXTURES, load_development_split, sha256, write_immutable, snapshot_report_inputs
from training.evaluate_behavior import money_equal, currency, ratio
from src.python.transaction_direction import score_head, validate_model
from src.python.verify_engine import MasroofEngine


class CandidateEngine(MasroofEngine):
    """Override scoring only. All inherited sender/semantic/entity guards stay."""
    def __init__(self, candidate):
        super().__init__()
        validate_model(candidate)
        if candidate["transaction"]["threshold"] != .7 or candidate["direction"]["incomeThreshold"] != .5:
            raise ValueError("Runtime shadow adapter requires the existing decision thresholds")
        self.candidate = candidate

    def _score_tokens(self, tokens):
        return score_head(self.candidate["transaction"], tokens)[1], score_head(self.candidate["direction"], tokens)[1]


def measure(engine, cases):
    tp = tn = fp = fn = 0
    directions = amounts = accepted = 0
    direction_eligible = amount_eligible = 0
    failures = []
    for case in cases:
        result = engine.predict(case["sender"], case["text"], case.get("isContact", False))
        expected, actual = case["include"], result["isValidTransaction"]
        if expected:
            tp += actual
            fn += not actual
        else:
            fp += actual
            tn += not actual
        if expected != actual:
            failures.append({"caseId": case["id"], "kind": "falsePositive" if actual else "falseNegative"})
        if expected:
            data = result.get("data") or {}
            accepted += actual
            if case.get("direction") is not None:
                direction_eligible += 1
                directions += actual and data.get("type") == case["direction"]
            if case.get("amount") is not None and case.get("currency") is not None:
                amount_eligible += 1
                amounts += actual and money_equal(data.get("amount"), case["amount"]) and currency(data.get("currency")) == currency(case["currency"])
    return {"cases": len(cases), "truePositives": tp, "trueNegatives": tn, "falsePositives": fp, "falseNegatives": fn,
            "directionAllEligible": ratio(directions, direction_eligible), "amountCurrencyAllEligible": ratio(amounts, amount_eligible),
            "acceptedEligible": accepted, "failures": failures}


def compare(candidate_path):
    records = json.loads(DATASET.read_text(encoding="utf-8"))
    _, validation, _ = load_development_split(records)
    model = json.loads(candidate_path.read_text(encoding="utf-8"))
    if model["training"]["datasetSha256"] != sha256(DATASET) or model["training"]["splitSha256"] != sha256(SPLIT):
        raise ValueError("Candidate does not identify this frozen dataset/split")
    validation_cases = [{"id": records[i]["recordId"], "text": records[i]["text"], "sender": "",
                         "include": records[i]["label"] in ("TRANSACTION_CREDIT", "TRANSACTION_DEBIT"),
                         "direction": {"CREDIT": "INCOME", "DEBIT": "EXPENSE"}.get(records[i]["type"]),
                         "amount": records[i].get("expected_amount"), "currency": records[i].get("expected_currency")}
                        for i in validation]
    frozen = []
    for name in ("test_suite_cases.json", "qa_adversarial_cases.json"):
        for case in json.loads((FIXTURES / name).read_text(encoding="utf-8"))["testCases"]:
            e = case["expected"]
            frozen.append({"id": case["id"], "sender": case["sender"], "text": case["body"], "include": e["isValidTransaction"],
                           "direction": e.get("type"), "amount": e.get("amount"), "currency": e.get("currency")})
    baseline, candidate = MasroofEngine(), CandidateEngine(model)
    scopes = {name: {"baseline": measure(baseline, cases), "candidate": measure(candidate, cases)}
              for name, cases in (("syntheticValidation", validation_cases), ("frozenRegression", frozen))}
    base, new = scopes["frozenRegression"]["baseline"], scopes["frozenRegression"]["candidate"]
    sources = [DATASET, SPLIT, candidate_path, ROOT / "data/models/masroof_model.json",
               ROOT / "src/python/verify_engine.py", ROOT / "src/python/legacy_transaction_model.py",
               ROOT / "src/python/transaction_direction.py", ROOT / "src/python/preprocessing.py",
               ROOT / "src/python/service_notice.py", ROOT / "config/contracts/service_notice.json",
               ROOT / "src/python/authorization_request.py", ROOT / "config/contracts/authorization_request.json", Path(__file__)]
    sources += [ROOT / "src/python/entity_text.py", ROOT / "config/contracts/entity_text.json"]
    sources += [ROOT / "training/corpus_io.py", ROOT / "training/evaluate_behavior.py"]
    sources += [FIXTURES / name for name in ("test_suite_cases.json", "qa_adversarial_cases.json")]
    return {"version": "1.0.0", "scope": "Synthetic development comparison; legacy baseline has historical family exposure; no independent accuracy claim",
            "inputSha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources},
            "adapter": "Same Python runtime guards, extraction and lexical direction overrides; only the score heads differ; .7/.5 thresholds unchanged",
            "measurements": scopes,
            "frozenClassificationNoRegression": new["falsePositives"] <= base["falsePositives"] and new["falseNegatives"] <= base["falseNegatives"],
            "promotionAllowed": False, "promotionReason": "Independent reviewed evidence and owner-approved thresholds are absent; runtime parity of a new integration is also required",
            "activeWeightsChanged": False, "reservedMerchantFinalTestInferred": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_]{1,40}", args.run_id):
        parser.error("Invalid run ID")
    report = compare(args.candidate.resolve())
    if not args.check:
        snapshot_report_inputs("comparison_" + args.run_id, report["inputSha256"])
    path = ROOT / f"data/reports/behavior/{args.run_id}_comparison.json"
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            raise ValueError("Comparison missing or stale")
    else:
        write_immutable(path, content)
    for scope, rows in report["measurements"].items():
        for name, values in rows.items():
            print(f"{scope} {name}: FP={values['falsePositives']}, FN={values['falseNegatives']}; direction={values['directionAllEligible']['correctOrCount']}/{values['directionAllEligible']['total']}")
    print("Promotion not authorized; active weights unchanged")


if __name__ == "__main__":
    main()
