"""Materialize separate source-text validation reviews; never predict, fit or admit."""
import argparse
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import json

from tools.contracts.validate_sms_semantics import validate_annotations, derive_tracking
from training.corpus.review_semantics import annotation, evidence, expand_decision, validate_review_policy
from training.corpus.propagation import build as proposal_build, VALIDATION_QUEUE, PLAN
from training.corpus.semantics import OUTPUT, digest, json_text, json_lines
from training.corpus_io import ROOT, DATASET, SPLIT, sha256, write_immutable, snapshot_report_inputs

DECISIONS = OUTPUT / "validation_review_decisions_v1.json"
REVIEWED = OUTPUT / "validation_text_reviews_v1.jsonl"
MANIFEST = OUTPUT / "validation_review_manifest_v1.json"
REPORT = ROOT / "data/reports/sms_semantics_validation_review_v1.json"
BASE_KEYS = {"queueIndex", "recordId", "textSha256", "status", "statusCue", "reviewNote"}
COMPLETED_KEYS = {"amountText", "currencyText", "direction", "relationship", "partyText", "purpose", "purposeCue"}


def materialize(decision, text):
    """Expand this explicit record decision only; no family or legacy-label inheritance."""
    status = decision["status"]
    if set(decision) != BASE_KEYS | (COMPLETED_KEYS if status == "completed" else set()):
        raise ValueError("Unexpected or missing review decision fields")
    if status != "completed":
        return expand_decision(decision, text)
    cue, note = decision["statusCue"], decision["reviewNote"]
    money, unit = decision["amountText"], decision["currencyText"]
    amount_span, unit_span = evidence(text, money), evidence(text, unit)
    if not (abs(amount_span["end"] - unit_span["start"]) <= 8 or abs(unit_span["end"] - amount_span["start"]) <= 8):
        raise ValueError("Reviewed currency is not attached to the primary amount")
    if unit not in ("JOD", "دينار"):
        raise ValueError("No explicit currency interpretation for this reviewed batch")
    fields = {
        "transactionStatus": annotation(text, status, cue, note),
        "amount": annotation(text, float(Decimal(money)), money, "Reviewed primary posted amount, not balance or identifier."),
        "currency": annotation(text, "JOD", unit, "Explicit Jordanian currency attached to the primary amount."),
        "currencyResolution": annotation(text, "explicit", unit, "Primary amount has an explicit currency token."),
        "direction": annotation(text, decision["direction"], cue, "Physical movement direction from the reviewed event. " + note),
        "transferRelationship": annotation(text, decision["relationship"], text, "Ownership is not inferred from party names or masks. " + note),
        "merchantOrCounterparty": annotation(text, decision["partyText"], decision["partyText"] or text,
                                            "Exact displayed named party/operator, or no named party in this event; account mask is not a merchant."),
    }
    tracking = derive_tracking(fields)
    if tracking is None:
        raise ValueError("Reviewed facts cannot establish a tracking decision")
    fields["trackingDecision"] = {
        "state": "weak", "value": tracking, "origin": "derived_policy", "reviewer": "assistant",
        "evidence": [{"kind": "annotation_field", "field": key} for key in
                     ("transactionStatus", "amount", "direction", "transferRelationship")],
        "note": "Recording policy applied to these weak reviewed facts; no model or generator class consulted.",
    }
    eligible = tracking == "include" and decision["direction"] == "outgoing"
    purpose, purpose_cue = decision["purpose"], decision["purposeCue"]
    if purpose is not None and (purpose != "Cash Withdrawals" or not eligible or not purpose_cue):
        raise ValueError("This batch has only an explicit cash-withdrawal purpose decision")
    if purpose is None and purpose_cue is not None:
        raise ValueError("Unused purpose evidence")
    fields["expenseCategory"] = annotation(text, purpose, purpose_cue or text,
                                          "Explicit withdrawal purpose." if purpose else "No unique expense purpose inferred from a merchant/operator name.")
    fields["categoryStatus"] = annotation(text, "assigned" if purpose else "uncertain" if eligible else "not_applicable",
                                         purpose_cue or text, "Purpose applies only to included outgoing events.")
    return fields


def validate_layer(rows, queue, sources, split):
    if len(rows) != len(queue) or len({row["recordId"] for row in rows}) != len(queue):
        raise ValueError("Validation reviews must cover the separate queue exactly once")
    by_id = {row["recordId"]: row for row in queue}
    groups = {index: group for group in split["groups"] for index in group["indices"]}
    validation = set(split["validationIndices"])
    for row in rows:
        base = by_id.get(row["recordId"])
        if base is None or set(row) != set(base):
            raise ValueError("Unknown validation record or record fields")
        if {k: v for k, v in row.items() if k not in ("annotations", "reviewState")} != {k: v for k, v in base.items() if k not in ("annotations", "reviewState")}:
            raise ValueError("Review changed source identity, fold, blocks or eligibility")
        index = row["sourceIndex"]
        if type(index) is not int or index not in validation or row["fold"] != "validation":
            raise ValueError("Review crossed the frozen validation fold")
        source, group = sources[index], groups[index]
        if row["recordId"] != source["recordId"] or row["textSha256"] != digest(source["text"]) or row["sourceExpressionId"] != source["sourceTemplateId"] or row["leakageGroupId"] != group["groupId"]:
            raise ValueError("Source, text or family binding changed")
        if row["reviewState"] != "weak_reviewed" or row["trainingEligible"] is not False or row["independentEvaluationEligible"] is not False:
            raise ValueError("Validation review cannot grant admission or human gold")
        if "transactionStatus" not in row["annotations"] or "trackingDecision" not in row["annotations"]:
            raise ValueError("Review omits completion or policy outcome")
        validate_annotations(row["annotations"], source["text"])
        validate_review_policy(row["annotations"])


def build(decision_file=None):
    _, queue, _, bound_outputs = proposal_build()
    for path, content in bound_outputs.items():
        if not path.exists() or path.read_bytes() != content.encode("utf-8"):
            raise ValueError("Bound proposal or validation queue is missing or stale")
    decisions = json.loads(DECISIONS.read_text(encoding="utf-8")) if decision_file is None else decision_file
    if decisions["schemaVersion"] != "1.0.0" or decisions["reviewer"] != "assistant" or decisions["sourceQueueSha256"] != sha256(VALIDATION_QUEUE) or decisions["sourceManifestSha256"] != sha256(PLAN):
        raise ValueError("Validation decisions do not bind the source queue/manifest/reviewer")
    sources = json.loads(DATASET.read_text(encoding="utf-8"))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = []
    for decision in decisions["reviews"]:
        index = decision["queueIndex"]
        if type(index) is not int or not 0 <= index < len(queue) or decision["recordId"] != queue[index]["recordId"] or decision["textSha256"] != queue[index]["textSha256"]:
            raise ValueError("Decision does not bind its exact validation queue item")
        row = deepcopy(queue[index])
        row["annotations"] = materialize(decision, sources[row["sourceIndex"]]["text"])
        row["reviewState"] = "weak_reviewed"
        rows.append(row)
    validate_layer(rows, queue, sources, split)
    unblocked = [row for row in rows if not row["admissionBlockers"]]
    def counts(records, field):
        return dict(Counter(row["annotations"][field]["value"] for row in records if field in row["annotations"]))
    report = {
        "version": "1.0.0", "scope": decisions["scope"], "reviewedValidationRepresentatives": len(rows),
        "weakFieldAnnotations": sum(len(row["annotations"]) for row in rows),
        "blockedRepresentatives": len(rows) - len(unblocked), "unblockedRepresentatives": len(unblocked),
        "statusCounts": counts(rows, "transactionStatus"), "trackingCounts": counts(rows, "trackingDecision"),
        "unblockedStatusCounts": counts(unblocked, "transactionStatus"),
        "unblockedTrackingCounts": counts(unblocked, "trackingDecision"),
        "unblockedCompletedDirectionCounts": counts([row for row in unblocked if row["annotations"]["transactionStatus"]["value"] == "completed"], "direction"),
        "unknownOwnershipRepresentatives": sum(row["annotations"].get("transferRelationship", {}).get("value") == "unknown" for row in rows),
        "unannotatedValidationDescendants": len(split["validationIndices"]) - len(rows),
        "trainingEligibleRecords": 0, "independentEvaluationEligibleRecords": 0,
        "studentPredictionsUsed": False, "modelFitted": False, "reservedMerchantFinalInferred": False,
        "limits": ["Assistant judgments are weak labels, not independent human gold or accuracy estimates.",
                   "Only 22 source-bound representatives reviewed; no descendant inheritance or fitting.",
                   "Protected/control blocks are retained even where source text was reviewed.",
                   "Uncertain completion leaves other fields unannotated; names do not resolve transfer ownership.",
                   "Both label classes and directions are represented, but four unblocked completed families cannot support precise accuracy claims."],
    }
    inputs = [*bound_outputs, DECISIONS, DATASET, SPLIT,
              ROOT / "training/corpus/validation_semantics.py", ROOT / "tests/python/test_sms_validation_review.py",
              ROOT / "training/corpus/review_semantics.py", ROOT / "tools/contracts/validate_sms_semantics.py",
              ROOT / "tools/contracts/validate_transaction_behavior.py", ROOT / "config/contracts/transaction_behavior.json",
              ROOT / "training/corpus_io.py"]
    hashes = {path.relative_to(ROOT).as_posix(): sha256(path) for path in inputs}
    report["inputSha256"] = hashes
    content = json_lines(rows)
    manifest = {"schemaVersion": "1.0.0", "scope": decisions["scope"], "inputSha256": hashes,
                "outputSha256": {REVIEWED.relative_to(ROOT).as_posix(): digest(content)},
                "trainingApplied": False, "admissionGranted": False}
    return rows, report, {REVIEWED: content, MANIFEST: json_text(manifest), REPORT: json_text(report)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    _, report, outputs = build()
    if args.check:
        if any(not path.exists() or path.read_bytes() != content.encode("utf-8") for path, content in outputs.items()):
            raise ValueError("Validation review missing or stale")
    else:
        if any(path.exists() and path.read_bytes() != content.encode("utf-8") for path, content in outputs.items()):
            raise ValueError("Changed validation review needs a new version")
        snapshot_report_inputs("sms_semantics_validation_review_v1", report["inputSha256"])
        for path, content in outputs.items():
            write_immutable(path, content)
    print(json_text({k: v for k, v in report.items() if k not in ("inputSha256", "limits")}))


if __name__ == "__main__":
    main()
