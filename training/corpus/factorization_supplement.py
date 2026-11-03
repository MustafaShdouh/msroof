"""Twelve existing training texts, source-defined coverage selection; no inference."""
import argparse
from collections import Counter
import json
from pathlib import Path

from training.corpus import factorization_pilot as pilot
from training.transactions.completion_adaptation import prepare, ROOT, PROTOCOL
from training.transactions.completion_encoder import digest

QUEUE = pilot.DIRECTORY / "supplement_queue.json"
REVIEWS = pilot.DIRECTORY / "supplement_reviews.json"
ANNOTATIONS = pilot.DIRECTORY / "supplement_annotations.jsonl"
REPORT = ROOT / "data/reports/transactions/sms_factorization_v1_supplement.json"
SOURCE_MANIFEST = ROOT / "data/annotations/sms_scope_v1/manifest.json"
SEED = "sms-factorization-supplement-2026-10-28"
PLAN = (("quotation", "illustrative_scope", [1,2]), ("negation", "negated_failure", [1,2]), ("party_name_scope", "party_scope", [1,3]))


def selection(training, original_queue, manifest):
    original_groups = {r["group"] for r in original_queue["rows"]}
    by_id = {r["recordId"]: r for r in training}
    chosen, families = [], []
    for topic, theme, states in PLAN:
        candidates = [g for g in manifest["families"] if g["theme"] == theme and g["fold"] == "proposed_training" and "scope-v1-"+g["id"] not in original_groups]
        if not candidates:
            raise ValueError("No eligible training family for "+topic)
        group = min(candidates, key=lambda g: pilot.hashed(SEED+":"+topic+":"+g["id"]))
        identifier = "scope-v1-"+group["id"]
        families.append(dict(topic=topic, theme=theme, familyId=identifier, semanticStates=states, candidateFamilies=sorted(g["id"] for g in candidates)))
        for state in states:
            for language in ("ar", "en"):
                record_id = f"{identifier}-{state}-{language}"
                if record_id not in by_id:
                    raise ValueError("Selected record is not in the frozen training view: "+record_id)
                chosen.append({**by_id[record_id], "topic":topic, "language":language, "semanticState":state})
    return chosen, families


def build():
    _, training, _, _ = prepare()
    pilot_annotations, _, pilot_outputs = pilot.build()
    # Earlier pilot outputs remain immutable; this supplement never refreshes them.
    for path, content in pilot_outputs.items():
        if path.read_bytes() != content.encode("utf-8"):
            raise ValueError("Original pilot output changed")
    original, manifest = pilot.read(pilot.QUEUE), pilot.read(SOURCE_MANIFEST)
    chosen, families = selection(training, original, manifest)
    queue, reviews, contract = pilot.read(QUEUE), pilot.read(REVIEWS), pilot.read(pilot.CONTRACT)
    if queue["selectionSeed"] != SEED or queue["rows"] != chosen or queue["families"] != families:
        raise ValueError("Frozen supplement selection changed")
    if queue["pilotQueueSha256"] != digest(pilot.QUEUE) or queue["sourceManifestSha256"] != digest(SOURCE_MANIFEST):
        raise ValueError("Source selection bindings changed")
    if reviews["reviewer"] != "assistant" or reviews["state"] != "weak":
        raise ValueError("Reviews cannot claim human gold")
    for document in (queue, reviews):
        for flag in ("modelPredictionsUsed", "trainingEligible", "independentEvaluationEligible", "modelFittingAllowed"):
            if document[flag] is not False: raise ValueError("Research boundary changed")
    old_ids = {r["recordId"] for r in original["rows"]}
    if len(chosen) != 12 or len({r["recordId"] for r in chosen}) != 12 or old_ids & {r["recordId"] for r in chosen}:
        raise ValueError("Supplement must have 12 new training records")
    by_id = {r["recordId"]: r for r in reviews["reviews"]}
    if len(reviews["reviews"]) != 12 or set(by_id) != {r["recordId"] for r in chosen}:
        raise ValueError("Manual reviews do not cover exact selection")
    annotations = [{**pilot.validate_review(r, by_id[r["recordId"]], contract), "topic":r["topic"], "language":r["language"]} for r in chosen]
    combined = pilot_annotations + annotations
    coverage = Counter(r["messageContext"]["value"] for r in combined if r["reviewState"] == "reviewed_weak")
    groups = {r["authoringGroupId"] for r in combined}
    report = dict(runId="sms_factorization_v1_supplement", inputSha256={p.relative_to(ROOT).as_posix():digest(p) for p in
        (PROTOCOL, pilot.CONTRACT, pilot.QUEUE, pilot.REVIEWS, pilot.ANNOTATIONS, pilot.AUDIT, SOURCE_MANIFEST, QUEUE, REVIEWS, Path(__file__), Path(pilot.__file__))},
        selectionKind="Source-theme/state-directed coverage supplement, not a random or label-blind sample; never model-score selected",
        records=12, families=families, languageCounts=dict(Counter(r["language"] for r in annotations)),
        contextCounts=dict(Counter(r["messageContext"]["value"] for r in annotations)), eventCounts=dict(Counter(r["describedEventState"]["value"] for r in annotations)),
        reviewStateCounts=dict(Counter(r["reviewState"] for r in annotations)),
        combinedRecords=len(combined), combinedReviewStateCounts=dict(Counter(r["reviewState"] for r in combined)),
        combinedReviewedContextCounts=dict(coverage), missingReviewedContexts=[c for c in contract["contextLabels"] if not coverage[c]],
        partiallyReviewedTrainingGroups=len(groups), groupsWithoutAnyFactorizedReview=129-len(groups),
        fullyReviewedTrainingGroups=0, unreviewedTrainingRecords=1158-len(combined), originalLabelsChanged=0,
        modelInference=False, modelFitted=False, reservedInferred=False,
        limits=["36 source-specific weak annotations are not a training-ready 1158-row factorized corpus.",
                "No propagation to counterpart, other semantic states or entire source family; remaining records are unreviewed.",
                "Known-other means message context, not the expense category Other. It does not authenticate a sender.",
                "The original held unknown context is retained; this supplement supplies no unheld unknown-context class example.",
                "Fixed contextual contrasts validate annotation applicability only, not model understanding or generalization."])
    outputs = {ANNOTATIONS:"".join(json.dumps(r,ensure_ascii=False,separators=(",",":"))+"\n" for r in annotations),
        REPORT:json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n"}
    return annotations, report, outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    _, report, outputs = build()
    for path, content in outputs.items():
        if path.exists():
            if path.read_bytes() != content.encode("utf-8"): raise ValueError("Frozen supplement differs")
        elif args.check: raise ValueError("Supplement missing")
        else:
            with path.open("x", encoding="utf-8", newline="\n") as handle: handle.write(content)
    print(json.dumps({k:report[k] for k in ("records","contextCounts","eventCounts","combinedReviewStateCounts","missingReviewedContexts","partiallyReviewedTrainingGroups","unreviewedTrainingRecords")}))


if __name__ == "__main__":
    main()
