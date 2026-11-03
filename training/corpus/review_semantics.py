"""Materialize explicit source-bound assistant reviews; no classifier or template expansion."""
import argparse
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import json

from tools.contracts.validate_sms_semantics import validate_record, derive_tracking, SCHEMA
from training.corpus.semantics import OUTPUT, DATASET, REPORT as PREPARATION_REPORT, digest, json_lines, json_text, prepare
from training.corpus_io import ROOT, sha256, snapshot_report_inputs, write_immutable

DECISIONS = OUTPUT / "text_review_decisions_v1.json"
REVIEWED = OUTPUT / "text_reviews_v1.jsonl"
MANIFEST = OUTPUT / "text_review_manifest_v2.json"
REPORT = ROOT / "data/reports/sms_semantics_text_review_v2.json"


def evidence(text, quote):
    start = text.find(quote)
    if not quote or start < 0:
        raise ValueError("Reviewed quote is missing from the bound source text")
    return {"kind": "text_span", "start": start, "end": start + len(quote), "text": quote}


def annotation(text, value, quote, note):
    return {"state": "weak", "value": value, "origin": "assistant_reviewed_text", "reviewer": "assistant",
            "evidence": [evidence(text, quote)], "note": note}


def expand_decision(decision, text):
    """Only explicit decisions on this record are expanded; no student/legacy predictions."""
    status, cue, note = decision["status"], decision["statusCue"], decision["reviewNote"]
    fields = {"transactionStatus": annotation(text, status, cue, note)}
    if status == "non_transaction":
        for field, value in {"amount": None, "currency": None, "currencyResolution": "not_applicable",
                             "direction": "not_applicable", "transferRelationship": "not_applicable",
                             "merchantOrCounterparty": None, "expenseCategory": None, "categoryStatus": "not_applicable"}.items():
            fields[field] = annotation(text, value, cue, "Not applicable to the reviewed non-transaction; mentioned money/entities are not a posted primary event. " + note)
    elif status == "completed":
        amount_quote, unit_quote = decision["amountText"], decision["currencyText"]
        amount_span, unit_span = evidence(text, amount_quote), evidence(text, unit_quote)
        if not (abs(amount_span["end"] - unit_span["start"]) <= 8 or abs(unit_span["end"] - amount_span["start"]) <= 8):
            raise ValueError("Reviewed currency quote is not attached to the selected transaction amount")
        fields["amount"] = annotation(text, float(Decimal(amount_quote)), amount_quote, "Reviewed primary transaction amount, not the following balance or identifier.")
        fields["currency"] = annotation(text, "JOD", unit_quote, "Explicit JOD/d.أ currency attached to the reviewed primary amount.")
        if unit_quote not in ("JOD", "د.أ"):
            raise ValueError("This reviewed batch has no decision for this currency term")
        fields["currencyResolution"] = annotation(text, "explicit", unit_quote, "The selected primary amount explicitly states its currency.")
        fields["direction"] = annotation(text, decision["direction"], cue if decision["direction"] != "uncertain" else text,
                                          "Reviewed physical direction; both owner role and grammatical event context matter. " + note)
        fields["transferRelationship"] = annotation(text, decision["relationship"], text,
                                                     "Do not infer own/external ownership from a name, phone or mask. " + note)
        if decision["partyReviewed"]:
            party = decision["partyText"]
            fields["merchantOrCounterparty"] = annotation(text, party, party or text,
                                                            "Exact displayed source party phrase; generic branch/agent is not a proper party name. " + note)
        track = derive_tracking(fields)
        if track is None:
            raise ValueError("Completed review lacks enough annotated facts for a decision")
        eligible = track == "include" and decision["direction"] == "outgoing"
        purpose = decision["purpose"] if eligible else None
        if purpose is not None and purpose != "Cash Withdrawals":
            raise ValueError("This batch contains no other explicitly reviewed purpose assignment")
        purpose_quote = "ATM Withdrawal" if purpose else text
        fields["expenseCategory"] = annotation(text, purpose, purpose_quote,
                                                "Explicit cash-withdrawal wording." if purpose else
                                                "Purpose is uncertain for eligible spending; otherwise category is not applicable. Merchant/biller identity alone is not unique purpose evidence.")
        fields["categoryStatus"] = annotation(text, "assigned" if purpose else "uncertain" if eligible else "not_applicable", purpose_quote,
                                               "Purpose applies only to included outgoing events; no merchant-category model was consulted.")
    elif status != "uncertain":
        raise ValueError("Unsupported reviewed status")
    # The truncated uncertain record deliberately leaves other fields unannotated.
    tracking = derive_tracking(fields)
    if tracking is None:
        raise ValueError("Review cannot establish a tracking decision")
    refs = ["transactionStatus"] if status != "completed" else (
        ["transactionStatus", "transferRelationship"] if fields["transferRelationship"]["value"] == "unknown" else
        ["transactionStatus", "amount", "direction", "transferRelationship"])
    fields["trackingDecision"] = {"state": "weak", "value": tracking, "origin": "derived_policy", "reviewer": "assistant",
                                  "evidence": [{"kind": "annotation_field", "field": key} for key in refs],
                                  "note": "Canonical recording policy applied to these cited weak facts, not a legacy class or model score."}
    return fields


def validate_layer(reviewed, drafts, queue, sources):
    base = {row["recordId"]: row for row in drafts}
    queued = {row["recordId"] for row in queue}
    if len(reviewed) != len(queue) or {row["recordId"] for row in reviewed} != queued:
        raise ValueError("Reviews must cover each queued training representative exactly once")
    for row in reviewed:
        original = base[row["recordId"]]
        if {key: value for key, value in row.items() if key != "annotations"} != {key: value for key, value in original.items() if key != "annotations"}:
            raise ValueError("Review altered source identity, fold, weak claims, blockers or admission flags")
        validate_record(row, sources[row["sourceIndex"]], row["sourceIndex"], "train", original["leakageGroupId"])
        validate_review_policy(row["annotations"])


def validate_review_policy(annotations):
    """Check annotated output states without filling unannotated fields or trusting a model."""
    def value(field):
        return annotations[field]["value"]
    status = value("transactionStatus")
    if status == "non_transaction":
        for field in ("amount", "currency", "merchantOrCounterparty", "expenseCategory"):
            if field in annotations and value(field) is not None:
                raise ValueError("A non-transaction cannot assert a posted primary financial field")
        for field in ("currencyResolution", "direction", "transferRelationship", "categoryStatus"):
            if field in annotations and value(field) != "not_applicable":
                raise ValueError("Non-transaction financial states must be not_applicable")
    if "categoryStatus" in annotations and "direction" in annotations:
        eligible = value("trackingDecision") == "include" and value("direction") == "outgoing"
        if not eligible and value("categoryStatus") != "not_applicable":
            raise ValueError("Noneligible records cannot assert an expense category state")
        if eligible and value("categoryStatus") not in ("assigned", "uncertain"):
            raise ValueError("Included outgoing category needs assigned or uncertain state")
        if "expenseCategory" in annotations and ((value("expenseCategory") is not None) != (value("categoryStatus") == "assigned")):
            raise ValueError("Expense purpose value and category state disagree")
    if "transferRelationship" in annotations and "direction" in annotations:
        if value("transferRelationship") == "own_accounts" and value("direction") != "not_applicable":
            raise ValueError("Own-account movement has no net direction")


def validate_prepared_bytes(manifest, folder=OUTPUT):
    if set(manifest["artifacts"]) != {"drafts.jsonl", "review_queue.jsonl"}:
        raise ValueError("Unknown preparation artifact path")
    for name, expected in manifest["artifacts"].items():
        if sha256(folder / name) != expected:
            raise ValueError("Preparation artifact bytes differ from the bound manifest")


def build():
    drafts, queue, _, _, prepared = prepare()
    for path, content in prepared.items():
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            raise ValueError("Preparation artifact missing or changed")
    validate_prepared_bytes(json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8")))
    decision_file = json.loads(DECISIONS.read_text(encoding="utf-8"))
    if decision_file["schemaVersion"] != "1.0.0" or decision_file["reviewer"] != "assistant" or decision_file["sourceManifestSha256"] != sha256(OUTPUT / "manifest.json"):
        raise ValueError("Review decisions do not bind the prepared manifest/reviewer")
    decisions = decision_file["reviews"]
    by_id = {row["recordId"]: row for row in drafts}
    sources = json.loads(DATASET.read_text(encoding="utf-8"))
    reviewed = []
    for decision in decisions:
        index = decision["queueIndex"]
        if type(index) is not int or not 0 <= index < len(queue) or queue[index]["recordId"] != decision["recordId"] or queue[index]["textSha256"] != decision["textSha256"]:
            raise ValueError("Review decision does not bind its queue record and text")
        row = deepcopy(by_id[decision["recordId"]])
        row["annotations"] = expand_decision(decision, sources[row["sourceIndex"]]["text"])
        reviewed.append(row)
    validate_layer(reviewed, drafts, queue, sources)
    status = Counter(row["annotations"]["transactionStatus"]["value"] for row in reviewed)
    tracking = Counter(row["annotations"]["trackingDecision"]["value"] for row in reviewed)
    coverage = {field: sum(field in row["annotations"] for row in reviewed) for field in SCHEMA["annotationFields"]}
    unblocked = [row for row in reviewed if not row["admissionBlockers"]]
    report = {"version": "1.0.1", "scope": "Assistant weak source-text review only; not human gold, data admission or independent accuracy",
              "reviewedRecords": len(reviewed), "weakFieldAnnotations": sum(len(row["annotations"]) for row in reviewed),
              "fieldCoverage": coverage, "statusCounts": dict(status), "trackingCounts": dict(tracking),
              "unblockedReviewedRecords": len(unblocked), "blockedReviewedRecords": len(reviewed) - len(unblocked),
              "unblockedStatusCounts": dict(Counter(row["annotations"]["transactionStatus"]["value"] for row in unblocked)),
              "purposeAssignments": dict(Counter(row["annotations"]["expenseCategory"]["value"] for row in reviewed
                                                 if row["annotations"].get("expenseCategory", {}).get("value") is not None)),
              "unannotatedFields": {row["recordId"]: [field for field in SCHEMA["annotationFields"] if field not in row["annotations"]]
                                     for row in reviewed if len(row["annotations"]) < len(SCHEMA["annotationFields"])},
              "trainingEligibleRecords": 0, "independentEvaluationEligibleRecords": 0,
              "assistantWeakAnnotations": True, "humanGold": False, "studentRuntimePredictionsUsed": False,
              "merchantFinalInferencePerformed": False, "teacherPredictionsTreatedAsGold": False,
              "modelFitted": False, "descendantAnnotationsPropagated": False,
              "limits": ["The named source account in queue7 has an unresolved party role; party remains unannotated.",
                         "Queue44 is a truncated prefix/date/balance fragment: reviewed completion uncertainty, other fields unannotated.",
                         "Transfer ownership is unknown without explicit facts; no own/external labels inferred from masks/names/phones.",
                         "Named merchants/billers alone do not establish unique purpose; only explicit ATM withdrawal is assigned in this batch."]}
    paths = [*prepared, DECISIONS, ROOT / "training/corpus/review_semantics.py", ROOT / "tests/python/test_sms_semantics_review.py"]
    hashes = {path.relative_to(ROOT).as_posix(): sha256(path) for path in paths}
    content = json_lines(reviewed)
    manifest = {"schemaVersion": "1.0.1", "sourceManifestSha256": sha256(OUTPUT / "manifest.json"),
                "reviewOrigin": "assistant_reviewed_text_not_human_gold", "inputSha256": hashes,
                "artifact": REVIEWED.relative_to(ROOT).as_posix(), "artifactSha256": digest(content),
                "trainingApplied": False, "humanGold": False}
    report["inputSha256"], report["artifactSha256"] = hashes, digest(content)
    return reviewed, report, {REVIEWED: content, MANIFEST: json_text(manifest), REPORT: json_text(report)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    _, report, outputs = build()
    if args.check:
        if any(not path.exists() or path.read_bytes() != content.encode("utf-8") for path, content in outputs.items()):
            raise ValueError("Text review artifact missing or stale")
    else:
        if any(path.exists() and path.read_bytes() != content.encode("utf-8") for path, content in outputs.items()):
            raise ValueError("Changed text review needs a new version")
        snapshot_report_inputs("sms_semantics_text_review_v2", report["inputSha256"])
        for path, content in outputs.items():
            write_immutable(path, content)
    print(json_text({key: report[key] for key in ("reviewedRecords", "weakFieldAnnotations", "statusCounts", "trackingCounts", "trainingEligibleRecords")}))


if __name__ == "__main__":
    main()
