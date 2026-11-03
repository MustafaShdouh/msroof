"""Summarize existing ML evidence and data gaps; never fit or infer reserved folds."""
import argparse
from collections import Counter
import json
import re

from src.python.engine import MasroofEngine
from training.corpus_io import DATASET, SPLIT, sha256, snapshot_report_inputs, write_immutable
from training.evaluation.detailed import ROOT, load
from training.evaluation.ownership import no_context_cases

CURRENT = "data/reports/behavior/arabic_message_semantics_v1.json"
CATEGORY = "data/reports/merchant_category_research_jordan_data_v3.json"
BIO = "data/reports/bio/context_labels_v2_context_v1_evaluation.json"
SCORE = "data/reports/transaction_direction_jordan_sanitized_v1_evaluation.json"
COMPARISONS = ["data/reports/behavior/jordan_sanitized_v1_final_comparison.json",
               "data/reports/behavior/jordan_sanitized_liblinear_v1_final_comparison.json"]
LABELS = "data/annotations/category_labels.jsonl"


def evaluate():
    current = load(CURRENT)
    hashes = dict(current["inputSha256"])
    # Bind fresh diagnostic counts to the engine that produced the current report.
    for path, expected in hashes.items():
        if sha256(ROOT / path) != expected:
            raise ValueError("Current behavior report source is stale: " + path)
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    if sha256(DATASET) != split["datasetSha256"]:
        raise ValueError("Training data no longer matches its frozen split")
    by_id = {row["recordId"]: row for row in data}
    label_rows = [json.loads(line) for line in (ROOT / LABELS).read_text(encoding="utf-8").splitlines() if line.strip()]
    canonical = ["transactionStatus", "trackingDecision", "transferRelationship", "direction", "expenseCategory"]
    engine, decisions, categories, review_reasons = MasroofEngine(), Counter(), Counter(), Counter()
    cases = no_context_cases()
    for case in cases:
        assessment = engine.predict_detailed(case["input"])
        decisions[assessment["trackingDecision"]] += 1
        if assessment["trackingDecision"] == "review":
            review_reasons.update(assessment["reasonCodes"])
        if assessment["trackingDecision"] == "include" and assessment["direction"] == "outgoing":
            categories[assessment["expenseCategory"] or "<uncertain>"] += 1
    comparisons = []
    for path in COMPARISONS:
        report = load(path)
        candidate = report["measurements"]["syntheticValidation"]["candidate"]
        failures = [row["caseId"] for row in candidate["failures"] if row["kind"] == "falseNegative"]
        if any(key not in by_id for key in failures):
            raise ValueError("Candidate failure ID is missing from the audited corpus")
        comparisons.append({"report": path, "validationCases": candidate["cases"],
                            "falsePositives": candidate["falsePositives"], "falseNegatives": candidate["falseNegatives"],
                            "missedSourceExpressions": dict(Counter(by_id[key]["sourceTemplateId"] for key in failures)),
                            "frozenFalseNegatives": report["measurements"]["frozenRegression"]["candidate"]["falseNegatives"],
                            "promotionAllowed": report["promotionAllowed"]})
    merchant = load(CATEGORY)
    variant = merchant["variants"][merchant["selectedResearchVariant"]]
    arabic = variant["validation"]["arabicObservedNames"]
    bio = load(BIO)
    contract = load("config/contracts/transaction_behavior.json")
    for path in (CURRENT, CATEGORY, BIO, SCORE, *COMPARISONS, LABELS,
                 DATASET.relative_to(ROOT).as_posix(), SPLIT.relative_to(ROOT).as_posix(),
                 "data/reports/category_evaluation_readiness.json", "data/annotations/CATEGORY_LABELING.md",
                 "training/evaluation/readiness.py"):
        hashes[path] = sha256(ROOT / path)
    included_outgoing = sum(categories.values())
    assigned = included_outgoing - categories["<uncertain>"]
    return {"version": "1.0.0", "scope": "Readiness audit of existing exposed development evidence; no independent accuracy claim",
            "inputSha256": hashes, "modelFitted": False, "activeModelChanged": False,
            "reservedMerchantFinalTestInferred": False,
            "corpus": {"records": len(data), "originCounts": dict(Counter(row["origin"] for row in data)),
                       "labelOriginCounts": dict(Counter(row["labelOrigin"] for row in data)),
                       "legacyLabelCounts": dict(Counter(row["label"] for row in data)),
                       "canonicalNamedTargetPresence": {key: sum(key in row for row in data) for key in canonical},
                       "legacyExtractionTargetPresence": {key: sum(key in row for row in data) for key in ("expected_amount", "expected_currency", "expected_merchant", "type")},
                       "folds": {fold: {"records": len(split[fold + "Indices"]),
                                         "sourceExpressions": len({data[index]["sourceTemplateId"] for index in split[fold + "Indices"]})}
                                 for fold in ("train", "validation")},
                       "interpretation": "Legacy class/type/expected fields provide weak targets; absent canonical names do not mean zero usable supervision. They do not establish ownership or purpose."},
            "publicDevelopmentDiagnostic": {"records": len(cases), "decisions": dict(decisions),
                                            "overlappingReviewReasons": dict(review_reasons), "includedOutgoing": included_outgoing,
                                            "assignedPurpose": assigned, "categoryPredictions": dict(categories),
                                            "conditionalAssignmentRate": assigned / included_outgoing if included_outgoing else None,
                                            "interpretation": "Output coverage among accepted outgoing controls, not accuracy or all-eligible coverage; records are not independent samples."},
            "candidates": {"transactionComparisons": comparisons,
                           "rawDirection": load(SCORE)["groupedValidation"]["directionOnActualTransactions"],
                           "bioValidationCount": bio["validationCount"], "bioCompleteFields": bio["bio"]["exactPrimaryFields"],
                           "wordCompleteFields": bio["wordComparator"]["exactPrimaryFields"], "regexCompleteFields": bio["regexValues"]["exactPrimaryFields"]},
            "purposeData": {"transactionLabelRecords": len(label_rows), "merchantTrainingBusinesses": variant["businessCount"],
                            "humanMerchantValidation": variant["validation"]["humanLabelsOnly"],
                            "arabicMerchantValidation": {key: value for key, value in arabic.items() if key != "records"},
                            "merchantFinalInferencePerformed": merchant["testInferencePerformed"],
                            "interpretation": "Merchant defaults are not transaction-purpose labels; assistant labels are not human gold."},
            "independentFinalEvaluationAvailable": contract["evaluation"]["independentFinalEvaluationAvailable"],
            "releaseThresholds": contract["evaluation"]["releaseThresholds"],
            "historicalActiveExportAccuracyClaim": load("data/models/masroof_model.json")["metadata"].get("accuracy"),
            "documentationConflict": ("CATEGORY_LABELING.md treats Other as unknown; approved transaction contract reserves Other for understood out-of-taxonomy purpose. Resolve before new label admission."
                                      if "Use `Other` only when a careful human review cannot choose" in (ROOT / "data/annotations/CATEGORY_LABELING.md").read_text(encoding="utf-8") else None),
            "recommendedNext": "Versioned field-level SMS annotation view over existing training-fold families; explicit provenance/evidence, unannotated distinct from uncertain, no fitting or teacher-as-gold."}


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
            raise ValueError("Readiness report missing or stale")
    else:
        snapshot_report_inputs("readiness_" + args.run_id, report["inputSha256"])
        write_immutable(path, content)
    print(json.dumps({"corpusRecords": report["corpus"]["records"],
                      "transactionPurposeLabels": report["purposeData"]["transactionLabelRecords"],
                      "includedOutgoing": report["publicDevelopmentDiagnostic"]["includedOutgoing"],
                      "assignedPurpose": report["publicDevelopmentDiagnostic"]["assignedPurpose"],
                      "independentFinalEvaluationAvailable": report["independentFinalEvaluationAvailable"]}, indent=2))


if __name__ == "__main__":
    main()
