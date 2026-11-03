"""Audit training event coverage and an authored weak batch; never infer, fit or admit."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import json
import re

from src.python.preprocessing import normalize_financial_numbers
from src.python.research.sms_semantics import normalize as feature_text
from src.python.research.merchant_category import normalize_name
from tools.contracts.validate_sms_semantics import validate_annotations
from training.corpus.review_semantics import (build as review_build, REVIEWED, MANIFEST as REVIEW_MANIFEST,
                                             validate_review_policy)
from training.corpus.semantics import (BUSINESSES, RESERVATION, FAMILIES, CONTROLS, reservation_forms,
                                      contained_texts, digest, json_text)
from training.corpus_io import ROOT, DATASET, sha256, write_immutable, snapshot_report_inputs

POLICY_PATH = ROOT / "config/contracts/sms_coverage_batch.json"
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
EVENTS = ROOT / "data/annotations/sms_coverage_v1/source_event_reviews.json"
BATCH = ROOT / "data/training/authored_sms_v1/messages.jsonl"
COHORT = ROOT / "data/reports/transactions/sms_semantics_ab_v1_cohort.json"
TRIAL_REPORT = ROOT / "data/reports/transactions/sms_semantics_ab_v1.json"
REPORT = ROOT / "data/reports/transactions/sms_coverage_batch_v1.json"
RECORD_FIELDS = {"recordId", "text", "textSha256", "sourceExpressionId", "authoringGroupId", "language", "eventType",
                 "origin", "fold", "annotations", "trainingEligible", "independentEvaluationEligible"}


def script(text):
    return "arabicContaining" if re.search(r"[\u0621-\u064a]", text) else "noArabic"


def validate_event_reviews(event_file, reviewed):
    if event_file["version"] != "1.0.0" or event_file["sourceReviewsSha256"] != sha256(REVIEWED) or event_file["sourceManifestSha256"] != sha256(REVIEW_MANIFEST):
        raise ValueError("Event reviews lost their source bindings")
    decisions = event_file["reviews"]
    if len(decisions) != len(reviewed) or len({row["recordId"] for row in decisions}) != len(reviewed):
        raise ValueError("Event review coverage must be exact and unique")
    by_id = {row["recordId"]: row for row in reviewed}
    for row in decisions:
        source = by_id.get(row["recordId"])
        if source is None or any(row[key] != source[key] for key in ("recordId", "textSha256", "sourceExpressionId")):
            raise ValueError("Event review source identity changed")
        if row["eventType"] not in POLICY["eventTypes"] or row["origin"] != "assistant_source_event_review" or row["state"] != "weak":
            raise ValueError("Event review cannot invent a type or claim human gold")


def validate_batch(rows):
    if len(rows) != POLICY["recordCount"] or len({row["recordId"] for row in rows}) != len(rows) or len({row["sourceExpressionId"] for row in rows}) != len(rows):
        raise ValueError("Authored batch must have exact unique record/expression coverage")
    groups = defaultdict(list)
    for row in rows:
        if set(row) != RECORD_FIELDS or not isinstance(row["text"], str) or not row["text"].strip() or row["textSha256"] != digest(row["text"]):
            raise ValueError("Authored record fields/text binding changed")
        if row["recordId"] != row["sourceExpressionId"] or not row["recordId"].startswith("authored-sms-v1-") or not row["authoringGroupId"].startswith("authored-v1-"):
            raise ValueError("New expressions cannot reuse old frozen source IDs")
        if row["origin"] != POLICY["origin"] or row["fold"] != POLICY["fold"] or row["trainingEligible"] is not False or row["independentEvaluationEligible"] is not False:
            raise ValueError("Authored examples cannot grant admission or independent evaluation")
        if row["language"] not in POLICY["languages"] or row["eventType"] not in POLICY["eventTypes"]:
            raise ValueError("Unsupported language/event tag")
        if (row["language"] == "ar") != (script(row["text"]) == "arabicContaining"):
            raise ValueError("Authored language tag disagrees with source script")
        fields = row["annotations"]
        if "transactionStatus" not in fields or "trackingDecision" not in fields:
            raise ValueError("Missing source-reviewed completion/policy annotation")
        if any(entry["state"] != "weak" or entry["reviewer"] != "assistant" for entry in fields.values()):
            raise ValueError("Authored fields must remain same-assistant weak labels")
        validate_annotations(fields, row["text"])
        validate_review_policy(fields)
        if fields["transactionStatus"]["value"] == "uncertain" and set(fields) != {"transactionStatus", "trackingDecision"}:
            raise ValueError("Unresolved completion must not fabricate posted financial facts in this batch")
        if fields["transactionStatus"]["value"] == "completed":
            primary = fields["amount"]
            if primary["value"] is not None:
                quote = primary["evidence"][0]["text"]
                if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", normalize_financial_numbers(quote)) or Decimal(normalize_financial_numbers(quote)) != Decimal(str(primary["value"])):
                    raise ValueError("Primary amount value does not match its exact financial-number span")
            elif fields["trackingDecision"]["value"] != "review":
                raise ValueError("Missing primary amount requires review")
            resolution, currency = fields["currencyResolution"]["value"], fields["currency"]["value"]
            if resolution == "explicit":
                units = {span["text"] for span in fields["currency"]["evidence"]}
                expected = "USD" if units == {"USD"} else "JOD" if units <= {"JOD", "د.أ", "دينار"} else None
                if expected is None or currency != expected:
                    raise ValueError("Currency interpretation changed from its source token")
            elif resolution != "default_missing" or currency != "JOD" or re.search(r"JOD|USD|دينار|د\.أ", row["text"]):
                raise ValueError("Default JOD cannot conceal an explicit currency")
        groups[row["authoringGroupId"]].append(row)
    if len(groups) != POLICY["authoringGroups"]:
        raise ValueError("Authoring scenario coverage changed")
    for records in groups.values():
        if len(records) != 2 or {row["language"] for row in records} != {"ar", "en"} or len({row["eventType"] for row in records}) != 1:
            raise ValueError("Bilingual counterparts must stay in one scenario group")
        values = [{key: entry["value"] for key, entry in row["annotations"].items()} for row in records]
        if values[0] != values[1]:
            raise ValueError("Paired scenario facts disagree across languages")


def overlap_blocks(rows, old_texts, forms):
    full = {normalize_name(text) for text in old_texts}
    masked = {feature_text(text) for text in old_texts}
    blocked = defaultdict(set)
    seen = defaultdict(list)
    for row in rows:
        text, proxy = normalize_name(row["text"]), feature_text(row["text"])
        seen[proxy].append(row["authoringGroupId"])
        if text in full:
            blocked[row["authoringGroupId"]].add("old_source_or_control_normalized_overlap")
        if proxy in masked:
            blocked[row["authoringGroupId"]].add("old_source_or_control_numeric_proxy_overlap")
        for form, reasons in forms.items():
            if " " + form + " " in " " + text + " ":
                blocked[row["authoringGroupId"]].update(reasons)
    for groups in seen.values():
        if len(groups) > 1:
            for group in groups:
                blocked[group].add("authored_numeric_proxy_duplicate")
    return {row["recordId"]: sorted(blocked[row["authoringGroupId"]]) for row in rows}


def support_table(cohort, event_reviews, sources):
    event_by_expression = {row["sourceExpressionId"]: row["eventType"] for row in event_reviews}
    table = {}
    for event in POLICY["eventTypes"]:
        cell = {}
        for language in ("arabicContaining", "noArabic"):
            selected = {head: [row for row in records if event_by_expression[row["sourceExpressionId"]] == event and script(sources[row["sourceIndex"]]["text"]) == language]
                        for head, records in cohort["training"].items()}
            cell[language] = {head: {"rows": len(records), "expressions": len({row["sourceExpressionId"] for row in records}),
                                   "targets": dict(Counter(row["target"] for row in records))} for head, records in selected.items()}
        table[event] = cell
    return table


def build():
    reviewed, _, original_outputs = review_build()
    for path, content in original_outputs.items():
        if path.read_bytes() != content.encode("utf-8"):
            raise ValueError("Original weak review missing/stale")
    cohort = json.loads(COHORT.read_text(encoding="utf-8"))
    trial = json.loads(TRIAL_REPORT.read_text(encoding="utf-8"))
    if sha256(COHORT) != trial["inputSha256"][COHORT.relative_to(ROOT).as_posix()]:
        raise ValueError("Measured reference cohort changed")
    event_file = json.loads(EVENTS.read_text(encoding="utf-8"))
    validate_event_reviews(event_file, reviewed)
    rows = [json.loads(line) for line in BATCH.read_text(encoding="utf-8").splitlines() if line.strip()]
    validate_batch(rows)
    sources = json.loads(DATASET.read_text(encoding="utf-8"))
    old_texts = [row["text"] for row in sources]
    for path in CONTROLS:
        old_texts.extend(contained_texts(json.loads(path.read_text(encoding="utf-8"))))
    businesses = [json.loads(line) for line in BUSINESSES.read_text(encoding="utf-8").splitlines() if line.strip()]
    forms = reservation_forms(businesses, json.loads(RESERVATION.read_text(encoding="utf-8"))["businessAssignments"],
                              json.loads(FAMILIES.read_text(encoding="utf-8"))["families"])
    blocks = overlap_blocks(rows, old_texts, forms)
    counts = Counter(row["annotations"]["transactionStatus"]["value"] for row in rows)
    report = {
        "version": "1.0.0", "scope": POLICY["scope"], "currentTrainingCoverage": support_table(cohort, event_file["reviews"], sources),
        "authoredBatch": {"records": len(rows), "authoringGroups": len({row["authoringGroupId"] for row in rows}),
                          "languageCounts": dict(Counter(row["language"] for row in rows)), "statusCounts": dict(counts),
                          "trackingCounts": dict(Counter(row["annotations"]["trackingDecision"]["value"] for row in rows)),
                          "eventCounts": dict(Counter(row["eventType"] for row in rows)),
                          "completedDirectionCounts": dict(Counter(row["annotations"]["direction"]["value"] for row in rows if row["annotations"]["transactionStatus"]["value"] == "completed")),
                          "blockersByRecord": blocks, "blockedRecords": sum(bool(value) for value in blocks.values()),
                          "unblockedButNotAdmittedRecords": sum(not value for value in blocks.values()),
                          "trainingEligibleRecords": 0, "independentEvaluationEligibleRecords": 0},
        "sourceReviewsCovered": len(event_file["reviews"]), "modelFitted": False, "studentPredictionsUsed": False,
        "reservedMerchantFinalInferred": False, "canonicalSourceRowsChanged": False,
        "limits": [POLICY["provenance"], "Exact/number-proxy/alias checks are bounded, not proof of template or semantic independence.",
                   "All 74 messages belong to proposed training only, with both eligibility flags false; no new test set is created.",
                   "Thirty-seven bilingual scenarios, not 74 independent real-world families; never split translation counterparts.",
                   "The original A/B trial and old validation remain exposed; no refit or release claim follows from authored coverage."]}
    paths = [POLICY_PATH, EVENTS, BATCH, COHORT, TRIAL_REPORT, REVIEWED, REVIEW_MANIFEST, DATASET, BUSINESSES, RESERVATION, FAMILIES, *CONTROLS,
             ROOT / "training/corpus/coverage.py", ROOT / "tests/python/test_sms_coverage.py",
             ROOT / "src/python/research/sms_semantics.py", ROOT / "config/contracts/sms_semantics_model.json",
             ROOT / "src/python/research/merchant_category.py", ROOT / "src/python/preprocessing.py",
             ROOT / "training/corpus/semantics.py", ROOT / "training/corpus/review_semantics.py",
             ROOT / "tools/contracts/validate_sms_semantics.py", ROOT / "config/contracts/sms_semantics_annotations.json",
             ROOT / "config/contracts/transaction_behavior.json", ROOT / "training/corpus_io.py"]
    report["inputSha256"] = {path.relative_to(ROOT).as_posix(): sha256(path) for path in paths}
    return rows, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    _, report = build()
    content = json_text(report)
    if args.check:
        if not REPORT.exists() or REPORT.read_bytes() != content.encode("utf-8"):
            raise ValueError("Coverage report missing/stale")
    else:
        if REPORT.exists() and REPORT.read_bytes() != content.encode("utf-8"):
            raise ValueError("Changed batch requires a new version")
        snapshot_report_inputs("sms_coverage_batch_v1", report["inputSha256"])
        write_immutable(REPORT, content)
    batch = report["authoredBatch"]
    print(json_text({key: batch[key] for key in ("records", "authoringGroups", "languageCounts", "statusCounts", "trackingCounts", "blockedRecords", "trainingEligibleRecords")}))


if __name__ == "__main__":
    main()
