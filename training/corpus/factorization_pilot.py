"""Audit training-group readiness and validate manually reviewed pilot sidecars."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from training.transactions.completion_adaptation import prepare, PROTOCOL, ROOT
from training.transactions.completion_encoder import digest

DIRECTORY = ROOT / "data/annotations/sms_factorization_v1"
CONTRACT = ROOT / "config/contracts/sms_factorization_annotations.json"
QUEUE = DIRECTORY / "pilot_queue.json"
REVIEWS = DIRECTORY / "reviews.json"
ANNOTATIONS = DIRECTORY / "pilot_annotations.jsonl"
AUDIT = ROOT / "data/reports/transactions/sms_factorization_v1_readiness.json"
SEED = "sms-factorization-pilot-2026-10-28"
STRATA = ("legacy_expression", "authored_coverage", "authored_context", "authored_scope")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def hashed(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def origin(group):
    for prefix, label in zip(("literal-", "authored-v1-", "context:", "scope-v1-"), STRATA):
        if group.startswith(prefix):
            return label
    raise ValueError("Unrecognized provenance group")


def selection(training):
    groups = defaultdict(list)
    for row in training:
        groups[row["group"]].append(row)
    chosen = []
    for stratum in STRATA:
        ordered = sorted((g for g in groups if origin(g) == stratum), key=lambda g: hashed(SEED+":group:"+g))[:6]
        for group in ordered:
            row = min(groups[group], key=lambda r: hashed(SEED+":record:"+r["recordId"]))
            chosen.append({**row, "originStratum": stratum})
    return groups, chosen


def span(text, quote):
    if not isinstance(quote, str) or not quote or text.count(quote) != 1:
        raise ValueError("Evidence must uniquely match exact raw source")
    start = text.index(quote)
    return dict(start=start, end=start+len(quote), text=quote, offsetUnit="unicode_code_point")


def validate_review(row, review, contract):
    if row["recordId"] != review["recordId"]:
        raise ValueError("Review/source alignment changed")
    if review["context"] not in contract["contextLabels"] or review["eventState"] not in contract["eventStateLabels"]:
        raise ValueError("Unrecognized semantic label")
    if not isinstance(review.get("note"), str) or not review["note"].strip():
        raise ValueError("Manual interpretation note required")
    review_state = review.get("reviewState", "reviewed_weak")
    holds = review.get("holdReasons", [])
    if review_state not in contract["reviewStates"] or (review_state == "hold") != bool(holds):
        raise ValueError("Hold disposition must have explicit reasons")
    return dict(recordId=row["recordId"], authoringGroupId=row["group"], sourceTextSha256=hashed(row["text"]),
        sourceFold="existing_research_training", originalCompletionTarget=row["target"], reviewState=review_state, reviewer="assistant",
        messageContext=dict(value=review["context"], evidence=[span(row["text"], review["contextQuote"])], state="weak"),
        describedEventState=dict(value=review["eventState"], evidence=[span(row["text"], review["eventQuote"])], state="weak"),
        note=review["note"], holdReasons=holds, trainingEligible=False, independentEvaluationEligible=False, modelFittingAllowed=False)


def build():
    _, training, _, _ = prepare()  # Hash-bound training view; never reads/scans predictions.
    groups, chosen = selection(training)
    queue, reviews, contract = read(QUEUE), read(REVIEWS), read(CONTRACT)
    if queue["rows"] != chosen or queue["selectionSeed"] != SEED or queue["trainingGroups"] != 129:
        raise ValueError("Frozen pilot selection changed")
    if Counter(origin(g) for g in groups) != queue["groupStrata"]:
        raise ValueError("Provenance inventory changed")
    if reviews["reviewer"] != "assistant" or reviews["state"] != "weak":
        raise ValueError("Pilot cannot claim human gold")
    for document in (queue, reviews, contract):
        for flag in ("trainingEligible", "independentEvaluationEligible", "modelFittingAllowed", "modelPredictionsUsed"):
            if document[flag] is not False:
                raise ValueError("Pilot admission or prediction boundary changed")
    if len(reviews["reviews"]) != 24 or len({r["recordId"] for r in reviews["reviews"]}) != 24:
        raise ValueError("Exactly 24 unique manual reviews required")
    review_by_id = {r["recordId"]: r for r in reviews["reviews"]}
    if set(review_by_id) != {r["recordId"] for r in chosen}:
        raise ValueError("Review IDs do not match fixed selection")
    annotations = [validate_review(r, review_by_id[r["recordId"]], contract) for r in chosen]
    inventory = []
    selected_ids = {r["recordId"] for r in chosen}
    for group, rows in sorted(groups.items()):
        pilot_ids = sorted(r["recordId"] for r in rows if r["recordId"] in selected_ids)
        stratum = origin(group)
        inventory.append(dict(group=group, originStratum=stratum, records=len(rows),
            rowIdSetSha256=hashed(json.dumps(sorted(r["recordId"] for r in rows), separators=(",", ":"))),
            originalTargetCounts=dict(Counter(r["target"] for r in rows)),
            originalTargetsMixed=len({r["target"] for r in rows}) > 1,
            availableEvidence={"legacy_expression":"source text and prior completion review",
                "authored_coverage":"prior financial-field annotations, not factorized labels",
                "authored_context":"bilingual contrast text, no factorized spans",
                "authored_scope":"eventMention/context/scope spans, not factorized categories"}[stratum],
            factorizedPilotReviewedIds=pilot_ids,
            readiness="partial_single_record_review" if pilot_ids else "not_reviewed_for_factorization",
            needsRecordLevelReview=True, automaticPropagationAllowed=False))
    context_counts = Counter(r["messageContext"]["value"] for r in annotations)
    event_counts = Counter(r["describedEventState"]["value"] for r in annotations)
    report = dict(runId="sms_factorization_v1_readiness", schemaVersion="1.0.0",
        inputSha256={p.relative_to(ROOT).as_posix(): digest(p) for p in (PROTOCOL, CONTRACT, QUEUE, REVIEWS, Path(__file__))},
        trainingViewSha256=read(PROTOCOL)["cohort"]["trainingViewSha256"], trainingRecords=1158, trainingGroups=129,
        groupsByProvenance=dict(Counter(origin(g) for g in groups)), rowsByProvenance=dict(Counter(origin(r["group"]) for r in training)),
        structurallyInventoriedGroups=len(inventory), semanticallyFullyReviewedGroups=0,
        partiallyReviewedGroups=24, untouchedFactorizationGroups=105, unreviewedTrainingRecords=1158-24,
        mixedTargetGroups=sum(g["originalTargetsMixed"] for g in inventory), pilotRecords=24,
        pilotContextCounts=dict(context_counts), pilotEventCounts=dict(event_counts),
        pilotReviewStateCounts=dict(Counter(r["reviewState"] for r in annotations)),
        pilotHeldIds=[r["recordId"] for r in annotations if r["reviewState"] == "hold"],
        missingReviewedContexts=[k for k in contract["contextLabels"] if not any(r["messageContext"]["value"] == k and r["reviewState"] == "reviewed_weak" for r in annotations)],
        missingPilotContexts=[k for k in contract["contextLabels"] if not context_counts[k]],
        missingPilotEventStates=[k for k in contract["eventStateLabels"] if not event_counts[k]],
        pilotLabelPairs=dict(Counter(r["messageContext"]["value"]+"/"+r["describedEventState"]["value"] for r in annotations)),
        originalLabelsChanged=0, modelInference=False, modelFitted=False, reservedInferred=False, inventory=inventory,
        limits=["Inventory is provenance/evidence readiness, not semantic review of all 129 groups or 1158 records.",
            "One reviewed pilot record does not label the other messages or bilingual counterpart in its group.",
            "Selection is fixed and prediction/label-blind within provenance strata. Missing themes must remain visible.",
            "Known-other context and no-event state distinguish clear absence/other purpose from semantic uncertainty.",
            "No automatic composition, source-authentication claim or canonical admission follows from these weak sidecars."])
    outputs = {ANNOTATIONS: "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":"))+"\n" for r in annotations),
        AUDIT: json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)+"\n"}
    return annotations, report, outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    _, report, outputs = build()
    for path, content in outputs.items():
        if path.exists():
            if path.read_bytes() != content.encode("utf-8"): raise ValueError("Frozen output changed: "+str(path))
        elif args.check:
            raise ValueError("Missing frozen output")
        else:
            with path.open("x", encoding="utf-8", newline="\n") as handle: handle.write(content)
    print(json.dumps({k:report[k] for k in ("trainingGroups", "pilotRecords", "mixedTargetGroups", "pilotContextCounts", "pilotEventCounts", "missingPilotContexts")}))


if __name__ == "__main__":
    main()
