"""Audit guarded weak-label expansion and admission candidates; never fit or admit data."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import json
import re

from src.python.entity_text import EntityText
from src.python.preprocessing import normalize_financial_numbers
from src.python.research.merchant_category import normalize_name
from training.corpus_io import ROOT, DATASET, SPLIT, sha256, write_immutable, snapshot_report_inputs
from training.corpus.semantics import (OUTPUT, BUSINESSES, RESERVATION, FAMILIES, CONTROLS, prepare,
                                      reservation_forms, group_blockers, contained_texts, digest, json_text, json_lines)
from training.corpus.review_semantics import build as review_build, REVIEWED, MANIFEST as REVIEW_MANIFEST

POLICY_PATH = ROOT / "config/contracts/sms_semantics_propagation.json"
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
RULES_PATH = ROOT / POLICY["riskPatternsSource"]
RULES = json.loads(RULES_PATH.read_text(encoding="utf-8"))
NUMBERS = re.compile(POLICY["numericPattern"], re.I | re.ASCII)
RISKS = [re.compile(RULES["patterns"][key], re.I | re.ASCII) for key in POLICY["riskPatternKeys"]]
RISKS.append(re.compile(POLICY["additionalRiskPattern"], re.I | re.ASCII))
PROPOSAL = OUTPUT / "propagation_proposal_v1.jsonl"
VALIDATION_QUEUE = OUTPUT / "validation_review_queue_v1.jsonl"
PLAN = OUTPUT / "propagation_manifest_v1.json"
REPORT = ROOT / "data/reports/sms_semantics_propagation_v1.json"


def normalize_text(text, routing=True):
    text = normalize_financial_numbers(text).replace("\\n", "\n").replace("\r", "")
    if routing and text.startswith(POLICY["routingPrefix"]):
        text = text[len(POLICY["routingPrefix"]):]
    return re.sub(r"\s+", " ", text).strip().casefold()


def frame(source):
    """A legacy name is merely a proposed exact source slot; never a target value."""
    text = normalize_text(source["text"])
    if POLICY["numericMarker"].casefold() in text or POLICY["partyMarker"].casefold() in text:
        raise ValueError("Source collides with a reserved slot marker")
    party = source.get("expected_merchant")
    party = normalize_text(party, routing=False) if isinstance(party, str) and party else None
    located = bool(party and any(char.isalpha() for char in party) and text.count(party) == 1)
    if located:
        text = text.replace(party, POLICY["partyMarker"], 1)
    tokens = [match.group() for match in NUMBERS.finditer(text)]
    return {"skeleton": NUMBERS.sub(POLICY["numericMarker"], text), "numbers": tokens,
            "partySlot": party if located else None, "textSignature": digest(normalize_text(source["text"]))}


def source_evidence(text, quote):
    view, needle = EntityText(text), EntityText(quote).text
    matches = list(re.finditer(re.escape(needle), view.text, re.I | re.ASCII))
    if len(matches) != 1:
        return None
    match = matches[0]
    start, end = view.starts[match.start()], view.ends[match.end() - 1]
    return {"start": start, "end": end, "text": text[start:end]}


def assess_guard(parent_source, child_source, reviewed):
    parent, child = frame(parent_source), frame(child_source)
    if parent["partySlot"] != child["partySlot"]:
        for slot in (parent["partySlot"], child["partySlot"]):
            if slot and any(pattern.search(slot) or pattern.search(EntityText(slot).text.casefold()) for pattern in RISKS):
                return "risky_changed_name_slot", child, {}
    if parent["skeleton"] != child["skeleton"]:
        return "literal_skeleton_changed", child, {}
    fields = reviewed["annotations"]
    if fields["transactionStatus"]["value"] == "completed":
        amount_text = normalize_text(fields["amount"]["evidence"][0]["text"])
        indices = [i for i, value in enumerate(parent["numbers"]) if value == amount_text]
        if len(indices) != 1:
            return "primary_slot_ambiguous", child, {}
        try:
            amount = Decimal(child["numbers"][indices[0]])
        except (InvalidOperation, IndexError):
            return "primary_slot_not_plain_decimal", child, {}
        if not amount.is_finite() or amount <= 0:
            return "primary_slot_not_positive", child, {}
    targets = {}
    for field in POLICY["allowedTargets"]:
        entry = fields.get(field)
        if not entry or (field == "direction" and (fields["transactionStatus"]["value"] != "completed" or entry["value"] not in POLICY["directionTargets"])):
            continue
        quote = entry["evidence"][0]["text"]
        span = source_evidence(child_source["text"], quote)
        if span is None:
            return "literal_evidence_not_unique", child, {}
        targets[field] = {"value": entry["value"], "origin": "proposed_from_weak_review",
                          "evidence": span, "proposedTrainingWeight": None}
    return None, child, targets


def deduplicate(proposals, signatures):
    groups = defaultdict(list)
    for row in proposals:
        if row["outcome"] == "candidate":
            groups[signatures[row["recordId"]]].append(row)
    for rows in groups.values():
        values = {json.dumps({key: value["value"] for key, value in row["candidateTargets"].items()}, sort_keys=True) for row in rows}
        if len(values) > 1:
            for row in rows:
                row["outcome"], row["reason"], row["candidateTargets"] = "hold", "conflicting_duplicate_targets", {}
            continue
        selected = min(rows, key=lambda row: (row["recordId"] != row["sourceReviewRecordId"], row["recordId"]))
        for row in rows:
            if row is not selected:
                row["outcome"], row["reason"], row["candidateTargets"] = "duplicate", "normalized_training_text_duplicate", {}
                row["duplicateOf"] = selected["recordId"]
    support = Counter((row["sourceExpressionId"], field) for row in proposals if row["outcome"] == "candidate" for field in row["candidateTargets"])
    for row in proposals:
        if row["outcome"] == "candidate":
            for field, target in row["candidateTargets"].items():
                target["proposedTrainingWeight"] = 1 / support[row["sourceExpressionId"], field]


def validate_proposals(proposals, drafts, sources, reviewed):
    originals = {row["recordId"]: row for row in drafts}
    parents = {row["recordId"]: row for row in reviewed}
    support = Counter((row["sourceExpressionId"], field) for row in proposals if row["outcome"] == "candidate" for field in row["candidateTargets"])
    candidates = {row["recordId"]: row for row in proposals if row["outcome"] == "candidate"}
    if len(proposals) != len(drafts) or {row["recordId"] for row in proposals} != set(originals):
        raise ValueError("Proposal must cover the existing training view exactly once")
    for row in proposals:
        base = originals[row["recordId"]]
        for key in ("sourceIndex", "textSha256", "sourceExpressionId", "leakageGroupId", "fold", "admissionBlockers"):
            if row[key] != base[key]:
                raise ValueError("Proposal changed source/fold/reservation metadata")
        if row["trainingEligible"] is not False or row["independentEvaluationEligible"] is not False or row["proposalOnly"] is not True:
            raise ValueError("Proposal cannot grant admission")
        if row["outcome"] not in ("candidate", "hold", "blocked", "duplicate"):
            raise ValueError("Unknown proposal outcome")
        if row["admissionBlockers"] and row["outcome"] != "blocked":
            raise ValueError("Existing reservation block was bypassed")
        parent = parents[row["sourceReviewRecordId"]]
        if parent["sourceExpressionId"] != row["sourceExpressionId"] or parent["leakageGroupId"] != row["leakageGroupId"]:
            raise ValueError("Proposal crosses reviewed expression/group")
        if set(row["candidateTargets"]) - set(POLICY["allowedTargets"]):
            raise ValueError("Unsupported field propagation")
        if row["outcome"] != "candidate" and row["candidateTargets"]:
            raise ValueError("Held/blocked/duplicate records cannot supply targets")
        if row["outcome"] == "candidate":
            if row["admissionBlockers"] or "transactionStatus" not in row["candidateTargets"]:
                raise ValueError("Blocked or unsupported candidate")
            error, _, expected_targets = assess_guard(sources[parent["sourceIndex"]], sources[row["sourceIndex"]], parent)
            if error or set(expected_targets) != set(row["candidateTargets"]):
                raise ValueError("Candidate does not pass its literal/slot guard")
            for field, target in row["candidateTargets"].items():
                weight = target.get("proposedTrainingWeight")
                if type(weight) not in (int, float) or not 0 < weight <= 1:
                    raise ValueError("Proposed sampling weight must be a positive finite number, not confidence")
                expected = parent["annotations"][field]["value"]
                allowed = POLICY["statusTargets"] if field == "transactionStatus" else POLICY["directionTargets"]
                if target["value"] != expected or target["value"] not in allowed:
                    raise ValueError("Candidate changed reviewed target")
                expected_targets[field]["proposedTrainingWeight"] = 1 / support[row["sourceExpressionId"], field]
                if target != expected_targets[field]:
                    raise ValueError("Proposed target, evidence, origin or weighting changed")
                span, text = target["evidence"], sources[row["sourceIndex"]]["text"]
                if not (type(span["start"]) is int and type(span["end"]) is int and 0 <= span["start"] < span["end"] <= len(text) and text[span["start"]:span["end"]] == span["text"]):
                    raise ValueError("Proposed evidence is not source-bound")
        if row["outcome"] == "duplicate":
            selected = candidates.get(row["duplicateOf"])
            if selected is None or normalize_text(sources[row["sourceIndex"]]["text"]) != normalize_text(sources[selected["sourceIndex"]]["text"]):
                raise ValueError("Duplicate does not reference an identical candidate text")


def build():
    reviewed, _, review_outputs = review_build()
    for path, content in review_outputs.items():
        if not path.exists() or path.read_bytes() != content.encode("utf-8"):
            raise ValueError("Bound text review is missing or stale")
    drafts, _, _, _, prep_outputs = prepare()
    sources = json.loads(DATASET.read_text(encoding="utf-8"))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    parents = {row["sourceExpressionId"]: row for row in reviewed}
    validation_signatures = {digest(normalize_text(sources[index]["text"])) for index in split["validationIndices"]}
    proposals, signatures = [], {}
    for base in drafts:
        parent = parents[base["sourceExpressionId"]]
        row = {key: base[key] for key in ("recordId", "sourceIndex", "textSha256", "sourceExpressionId", "leakageGroupId", "fold", "admissionBlockers")}
        row.update(sourceReviewRecordId=parent["recordId"], proposalOnly=True, trainingEligible=False,
                   independentEvaluationEligible=False, candidateTargets={}, duplicateOf=None)
        if base["admissionBlockers"]:
            row.update(outcome="blocked", reason="existing_admission_block")
        elif parent["annotations"]["transactionStatus"]["value"] not in POLICY["statusTargets"]:
            row.update(outcome="hold", reason="unsupported_uncertain_completion")
        else:
            reason, compared, targets = assess_guard(sources[parent["sourceIndex"]], sources[base["sourceIndex"]], parent)
            if compared["textSignature"] in validation_signatures:
                reason, targets = "validation_normalized_text_overlap", {}
            row.update(outcome="hold" if reason else "candidate", reason=reason or "literal_guard_passed", candidateTargets=targets)
            signatures[row["recordId"]] = compared["textSignature"]
        proposals.append(row)
    raw_candidates = sum(row["outcome"] == "candidate" for row in proposals)
    deduplicate(proposals, signatures)
    validate_proposals(proposals, drafts, sources, reviewed)
    # Evaluation annotation gets separate references only: no proposed target labels.
    businesses = [json.loads(line) for line in BUSINESSES.read_text(encoding="utf-8").splitlines() if line.strip()]
    assignments = json.loads(RESERVATION.read_text(encoding="utf-8"))["businessAssignments"]
    forms = reservation_forms(businesses, assignments, json.loads(FAMILIES.read_text(encoding="utf-8"))["families"])
    val_set = set(split["validationIndices"])
    groups = [group for group in split["groups"] if set(group["indices"]) <= val_set]
    forbidden_controls = defaultdict(set)
    for path in CONTROLS:
        for text in contained_texts(json.loads(path.read_text(encoding="utf-8"))):
            forbidden_controls[digest(normalize_name(text))].add("frozen_or_control_text_overlap")
    blockers = group_blockers(sources, groups, forms, forbidden_controls)
    train_signatures = {digest(normalize_text(sources[row["sourceIndex"]]["text"])) for row in drafts}
    validation_queue = []
    for group in sorted(groups, key=lambda group: group["groupId"]):
        for expression in sorted(group["sourceTemplateIds"]):
            index = min((i for i in group["indices"] if sources[i]["sourceTemplateId"] == expression),
                        key=lambda i: (digest(sources[i]["text"]), sources[i]["recordId"]))
            reasons = list(blockers[group["groupId"]])
            if any(digest(normalize_text(sources[i]["text"])) in train_signatures for i in group["indices"]):
                reasons.append("training_normalized_text_overlap")
            validation_queue.append({"recordId": sources[index]["recordId"], "sourceIndex": index,
                                     "textSha256": digest(sources[index]["text"]), "sourceExpressionId": expression,
                                     "leakageGroupId": group["groupId"], "fold": "validation", "annotations": {},
                                     "admissionBlockers": sorted(set(reasons)), "trainingEligible": False,
                                     "independentEvaluationEligible": False, "reviewState": "unreviewed"})
    candidates = [row for row in proposals if row["outcome"] == "candidate"]
    report = {"version": "1.0.0", "scope": POLICY["scope"], "trainingRecordsAudited": len(proposals),
              "rawGuardCandidatesBeforeDedup": raw_candidates, "outcomeCounts": dict(Counter(row["outcome"] for row in proposals)),
              "reasonCounts": dict(Counter(row["reason"] for row in proposals)),
              "candidateStatusCounts": dict(Counter(row["candidateTargets"]["transactionStatus"]["value"] for row in candidates)),
              "candidateDirectionCounts": dict(Counter(row["candidateTargets"]["direction"]["value"] for row in candidates if "direction" in row["candidateTargets"])),
              "candidateSourceExpressions": len({row["sourceExpressionId"] for row in candidates}),
              "directReviewedCandidates": sum(row["recordId"] == row["sourceReviewRecordId"] for row in candidates),
              "proposedDescendantCandidates": sum(row["recordId"] != row["sourceReviewRecordId"] for row in candidates),
              "validationQueueReferences": len(validation_queue), "validationQueueBlocked": sum(bool(row["admissionBlockers"]) for row in validation_queue),
              "validationTargetsAnnotated": 0, "trainingEligibleRecords": 0, "independentEvaluationEligibleRecords": 0,
              "modelFitted": False, "studentPredictionsUsed": False, "reservedMerchantFinalInferred": False,
              "limits": ["Passing literal/slot guards is a weak-label proposal, not semantic proof, per-record review or admission.",
                         "Legacy name metadata is an untrusted exact-span locator; risky changed slot wording holds the record out.",
                         "No ownership, purpose, tracking, amount/currency or party annotations are propagated.",
                         "Raw slot variations are not independent examples; duplicates are removed and each expression has proposed weight1 per head.",
                         "Unreviewed validation references carry no target labels and do not establish an independent test."]}
    inputs = [*prep_outputs, *review_outputs, POLICY_PATH, RULES_PATH, SPLIT, DATASET, BUSINESSES, RESERVATION, FAMILIES, *CONTROLS,
              ROOT / "training/corpus/propagation.py", ROOT / "tests/python/test_sms_semantics_propagation.py",
              ROOT / "src/python/entity_text.py", ROOT / "src/python/preprocessing.py"]
    hashes = {path.relative_to(ROOT).as_posix(): sha256(path) for path in inputs}
    contents = {PROPOSAL: json_lines(proposals), VALIDATION_QUEUE: json_lines(validation_queue)}
    manifest = {"schemaVersion": POLICY["schemaVersion"], "scope": POLICY["scope"], "inputSha256": hashes,
                "reviewDataSha256": sha256(REVIEWED), "reviewManifestSha256": sha256(REVIEW_MANIFEST),
                "outputSha256": {path.relative_to(ROOT).as_posix(): digest(content) for path, content in contents.items()},
                "admissionGranted": False, "trainingApplied": False}
    report["inputSha256"] = hashes
    return proposals, validation_queue, report, {**contents, PLAN: json_text(manifest), REPORT: json_text(report)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    _, _, report, outputs = build()
    if args.check:
        if any(not path.exists() or path.read_bytes() != content.encode("utf-8") for path, content in outputs.items()):
            raise ValueError("Propagation proposal missing or stale")
    else:
        if any(path.exists() and path.read_bytes() != content.encode("utf-8") for path, content in outputs.items()):
            raise ValueError("Changed proposal needs a new version")
        snapshot_report_inputs("sms_semantics_propagation_v1", report["inputSha256"])
        for path, content in outputs.items():
            write_immutable(path, content)
    print(json_text({key: report[key] for key in ("trainingRecordsAudited", "rawGuardCandidatesBeforeDedup", "outcomeCounts", "candidateStatusCounts", "candidateDirectionCounts", "validationQueueReferences", "trainingEligibleRecords")}))


if __name__ == "__main__":
    main()
