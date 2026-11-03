"""Reference-only synthetic SMS drafts and a training-family review queue; no inference."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json

from src.python.research.merchant_category import normalize_name
from tools.contracts.validate_sms_semantics import SCHEMA, validate_record
from training.corpus_io import ROOT, DATASET, SPLIT, FIXTURES, load_development_split, sha256, snapshot_report_inputs, write_immutable

OUTPUT = ROOT / "data/annotations/sms_semantics_v1"
REPORT = ROOT / "data/reports/sms_semantics_preparation_v1.json"
BUSINESSES = ROOT / "data/annotations/businesses_200.jsonl"
RESERVATION = ROOT / "data/training/splits/category_brand_split.json"
FAMILIES = ROOT / "data/sources/businesses/brand_families.json"
RESERVATION_SHA = "e2cfb583d1b62b9af72df0b985c6cdc84601bf052dc279dee4d611175c9fe99d"
CONTROLS = [FIXTURES / "test_suite_cases.json", FIXTURES / "qa_adversarial_cases.json"] + [
    ROOT / ("tests/fixtures/" + name + ".json") for name in (
        "transaction_behavior_cases", "detailed_assessment_cases", "authorization_request_cases",
        "ownership_context_cases", "paired_movement_cases", "arabic_message_semantics_cases")]


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def json_lines(rows):
    return "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def reservation_forms(businesses, assignments, families):
    """Use names/aliases and family metadata only, never category labels or predictions."""
    forms = defaultdict(set)
    for row in businesses:
        fold = assignments[row["businessId"]]
        if fold in ("validation", "test"):
            for form in [row["name"], *row["aliases"]]:
                if normalize_name(form):
                    forms[normalize_name(form)].add("protected_merchant:" + row["businessId"] + ":" + fold)
    for family in families:
        members = {normalize_name(name) for name in family["members"]}
        protected = {assignments[row["businessId"]] for row in businesses
                     if any(normalize_name(form) in members for form in [row["name"], *row["aliases"]])
                     and assignments[row["businessId"]] in ("validation", "test")}
        if protected:
            for form in members:
                if form:
                    forms[form].add("protected_brand_family:" + family["familyId"])
    return forms


def contained_texts(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("text", "body") and isinstance(item, str):
                yield item
            elif isinstance(item, (dict, list)):
                yield from contained_texts(item)
    elif isinstance(value, list):
        for item in value:
            yield from contained_texts(item)


def group_blockers(records, groups, forms, forbidden=None):
    result = {}
    for group in groups:
        blocked = set()
        for index in group["indices"]:
            text = " " + normalize_name(records[index]["text"]) + " "
            blocked.update((forbidden or {}).get(digest(text.strip()), []))
            for form, reasons in forms.items():
                if " " + form + " " in text:
                    blocked.update(reasons)
        result[group["groupId"]] = sorted(blocked)
    return result


def choose_queue(drafts):
    families = defaultdict(list)
    for row in drafts:
        families[row["sourceExpressionId"]].append(row)
    return [{"sourceExpressionId": family, "recordId": chosen["recordId"],
             "leakageGroupId": chosen["leakageGroupId"], "textSha256": chosen["textSha256"],
             "admissionBlockers": chosen["admissionBlockers"], "reviewState": "unreviewed"}
            for family, rows in sorted(families.items())
            for chosen in [min(rows, key=lambda row: (row["textSha256"], row["recordId"]))]]


def validate_view(drafts, queue, records, split, blockers):
    train = set(split["trainIndices"])
    group_by_index = {index: group["groupId"] for group in split["groups"] for index in group["indices"]}
    if len(drafts) != len(train) or {row["sourceIndex"] for row in drafts} != train or len({row["recordId"] for row in drafts}) != len(drafts):
        raise ValueError("Drafts must cover the existing training fold exactly once")
    for row in drafts:
        index = row["sourceIndex"]
        if type(index) is not int or index not in train:
            raise ValueError("Draft source is outside the training fold")
        validate_record(row, records[index], index, "train", group_by_index[index])
        if row["admissionBlockers"] != blockers[group_by_index[index]]:
            raise ValueError("Protected-identity blockers were removed or changed")
    if queue != choose_queue(drafts):
        raise ValueError("Queue is not the deterministic training-expression representative set")


def prepare():
    records = json.loads(DATASET.read_text(encoding="utf-8"))
    train, validation, split = load_development_split(records)
    if sha256(RESERVATION) != RESERVATION_SHA:
        raise ValueError("Protected merchant reservation changed")
    businesses = [json.loads(line) for line in BUSINESSES.read_text(encoding="utf-8").splitlines() if line.strip()]
    assignments = json.loads(RESERVATION.read_text(encoding="utf-8"))["businessAssignments"]
    families = json.loads(FAMILIES.read_text(encoding="utf-8"))["families"]
    forbidden = defaultdict(set)
    for index in validation:
        forbidden[digest(normalize_name(records[index]["text"]))].add("validation_text_overlap")
    for path in CONTROLS:
        for text in contained_texts(json.loads(path.read_text(encoding="utf-8"))):
            forbidden[digest(normalize_name(text))].add("frozen_or_control_text_overlap")
    train_set = set(train)
    train_groups = [group for group in split["groups"] if set(group["indices"]) <= train_set]
    blockers = group_blockers(records, train_groups, reservation_forms(businesses, assignments, families), forbidden)
    group_by_index = {index: group["groupId"] for group in split["groups"] for index in group["indices"]}
    drafts = [{"recordId": records[index]["recordId"], "sourceIndex": index,
               "textSha256": digest(records[index]["text"]), "sourceExpressionId": records[index]["sourceTemplateId"],
               "leakageGroupId": group_by_index[index], "fold": "train",
               "legacyClaims": {key: records[index][field] for key, field in SCHEMA["legacyFields"].items()},
               "annotations": {}, "admissionBlockers": blockers[group_by_index[index]],
               "trainingEligible": False, "independentEvaluationEligible": False}
              for index in sorted(train)]
    queue = choose_queue(drafts)
    validate_view(drafts, queue, records, split, blockers)
    paths = [DATASET, SPLIT, BUSINESSES, RESERVATION, FAMILIES, *CONTROLS, ROOT / "config/contracts/sms_semantics_annotations.json",
             ROOT / SCHEMA["semanticsSource"], ROOT / SCHEMA["provenanceConventionSource"],
             ROOT / "tools/contracts/validate_sms_semantics.py", ROOT / "training/corpus/semantics.py",
             ROOT / "tests/python/test_sms_semantics_preparation.py",
             ROOT / "training/corpus_io.py", ROOT / "src/python/research/merchant_category.py", ROOT / "src/python/preprocessing.py"]
    hashes = {path.relative_to(ROOT).as_posix(): sha256(path) for path in paths}
    draft_content, queue_content = json_lines(drafts), json_lines(queue)
    manifest = {"schemaVersion": SCHEMA["schemaVersion"], "scope": SCHEMA["scope"], "inputSha256": hashes,
                "sourceArtifact": DATASET.relative_to(ROOT).as_posix(), "splitArtifact": SPLIT.relative_to(ROOT).as_posix(),
                "legacyClaimOrigin": SCHEMA["legacyClaimOrigin"], "reviewQueueRule": SCHEMA["queueRule"],
                "artifacts": {"drafts.jsonl": digest(draft_content), "review_queue.jsonl": digest(queue_content)},
                "draftCount": len(drafts), "reviewQueueCount": len(queue), "untouchedValidationCount": len(validation),
                "sourceTextsDuplicated": False, "modelPredictionsUsed": False, "newSyntheticMessagesGenerated": False,
                "trainingApplied": False, "reservedMerchantFinalInferred": False}
    report = {"version": "1.0.0", "scope": SCHEMA["scope"], "inputSha256": hashes,
              "drafts": len(drafts), "sourceExpressionsInQueue": len(queue), "untouchedValidationRecords": len(validation),
              "weakLegacyClaimRecords": len(drafts), "annotatedCanonicalFields": 0,
              "canonicalAnnotationState": "unannotated; no claim of semantic uncertainty or confirmed absence",
              "legacyClassCounts": dict(sorted(Counter(row["legacyClaims"]["class"] for row in drafts).items())),
              "protectedDraftRecords": sum(bool(row["admissionBlockers"]) for row in drafts),
              "protectedQueueEntries": sum(bool(row["admissionBlockers"]) for row in queue),
              "blockerKindsByDraft": dict(Counter(kind for row in drafts for kind in {reason.split(":")[0] for reason in row["admissionBlockers"]})),
              "trainingEligibleRecords": 0, "independentEvaluationEligibleRecords": 0,
              "teacherPredictionsUsed": False, "newMessagesGenerated": False, "modelFitted": False,
              "artifactsSha256": manifest["artifacts"],
              "limits": ["Queue preparation is not completion of the80 text reviews.",
                         "Reserved lexical candidates are conservative/bounded and do not prove merchant identity; whole SMS groups are blocked without repartition.",
                         "Validation/frozen/control normalized-text matches block groups; this is not proof of exhaustive semantic/template isolation.",
                         "Legacy null fields are not confirmed absence; an empty annotations object is unannotated.",
                         "Reviewing a representative does not automatically label descendants or grant training admission."]}
    return drafts, queue, manifest, report, {OUTPUT / "drafts.jsonl": draft_content,
                                           OUTPUT / "review_queue.jsonl": queue_content,
                                           OUTPUT / "manifest.json": json_text(manifest), REPORT: json_text(report)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--queue-index", type=int)
    args = parser.parse_args()
    drafts, queue, manifest, report, outputs = prepare()
    if args.queue_index is not None:
        if not 0 <= args.queue_index < len(queue):
            parser.error("Queue index is outside the training review queue")
        selected = next(row for row in drafts if row["recordId"] == queue[args.queue_index]["recordId"])
        records = json.loads(DATASET.read_text(encoding="utf-8"))
        print(json_text({"queue": queue[args.queue_index], "draft": selected, "sourceText": records[selected["sourceIndex"]]["text"]}))
        return
    if args.check:
        for path, content in outputs.items():
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise ValueError("Preparation artifact missing/stale: " + path.relative_to(ROOT).as_posix())
    else:
        # Check every existing output before writing any new one.
        for path, content in outputs.items():
            if path.exists() and path.read_text(encoding="utf-8") != content:
                raise ValueError("Changed preparation needs a new version: " + path.name)
        snapshot_report_inputs("sms_semantics_preparation_v1", manifest["inputSha256"])
        for path, content in outputs.items():
            write_immutable(path, content)
    print(json_text({key: report[key] for key in ("drafts", "sourceExpressionsInQueue", "protectedQueueEntries", "untouchedValidationRecords", "trainingEligibleRecords")}))


if __name__ == "__main__":
    main()
