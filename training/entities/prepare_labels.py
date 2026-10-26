"""Versioned primary-slot BIO corrections and reservation-aware grouping."""
from collections import Counter, defaultdict
from decimal import Decimal
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from training.corpus_io import BIO, FIXTURES, sha256, write_immutable, snapshot_report_inputs
from training.entities.perceptron import normalize_token
from src.python.entity_text import EntityText
from src.python.engine import MasroofEngine
from src.python.preprocessing import normalize_financial_numbers

REVIEW = ROOT / "data/annotations/entities/bio_v2_review.json"
POLICY = ROOT / "config/contracts/bio_annotations.json"
DATA = ROOT / "data/training/sanitized_v2/bio_training_data.json"
SPLIT = ROOT / "data/training/splits/bio_sanitized_v2.json"
REPORT = ROOT / "data/reports/bio/bio_annotation_v2.json"
BUSINESSES = ROOT / "data/annotations/businesses_200.jsonl"
RESERVATION = ROOT / "data/training/splits/category_brand_split.json"
FAMILIES = ROOT / "data/sources/businesses/brand_families.json"
RESERVATION_HASH = "e2cfb583d1b62b9af72df0b985c6cdc84601bf052dc279dee4d611175c9fe99d"


CURRENCY_TERMS = (
    "USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|TRY|BRL|MXN|ZAR|JOD|SAR|AED|KWD|QAR|"
    "BHD|OMR|EGP|ILS|IQD|LBP|SR|KD|BD|RO|QR|DH|DHS|د\\.أ|دينار|دنانير|دينارا|"
    "ر\\.س|ريال|ريالات|ريالا|د\\.إ|درهم|دراهم|درهما|د\\.ك|ر\\.ق|د\\.ب|ر\\.ع|"
    "ج\\.م|جنيه|جنيها|\\$|€|£|¥|₹|₪"
)

CURRENCY_TOKEN_PATTERN = (
    r"(?<![A-Za-z\u0621-\u064A])(?:" + CURRENCY_TERMS + r")(?![A-Za-z\u0621-\u064A])"
)

TOKEN_RE = re.compile(
    r"(?:[0-9]{2,4}\*[0-9]{2,4}|xxxx[0-9]{3,4}|\*[0-9]{4})"
    r"|(?:" + CURRENCY_TOKEN_PATTERN + r")"
    r"|(?:[0-9]+(?:[,.'][0-9]+)*)"
    r"|(?:[A-Za-z\u0621-\u064A\u064B-\u065F]+)"
    r"|(?:\S)",
    re.IGNORECASE,
)


def split_examples(examples: list[dict]) -> tuple[list[dict], list[dict], list[str]]:
    """Keep each fixture source category in one deterministic split.

    Source categories are a coarse grouping proxy. The report records the
    selected groups so these metrics cannot be mistaken for template isolation.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for example in examples:
        groups[example["sourceCategory"]].append(example)
    entries = sorted(groups.items())
    randomizer = random.Random(20261024)
    randomizer.shuffle(entries)
    target = max(1, round(len(examples) * 0.20))
    selected: list[str] = []
    selected_count = 0
    for group_name, group_examples in entries:
        if selected_count >= target:
            break
        selected.append(group_name)
        selected_count += len(group_examples)
    validation_groups = set(selected)
    validation = [example for example in examples if example["sourceCategory"] in validation_groups]
    training = [example for example in examples if example["sourceCategory"] not in validation_groups]
    if not training or not validation:
        raise ValueError("BIO group split must contain train and validation examples")
    return training, validation, sorted(validation_groups)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def normalize(value):
    return MasroofEngine.normalize_merchant(normalize_financial_numbers(value))


def source_tokens(text):
    """Match on a normalized view; return raw tokens and original coordinates."""
    view = EntityText(text)
    tokens = []
    for match in TOKEN_RE.finditer(view.text):
        start, end = view.starts[match.start()], view.ends[match.end() - 1]
        tokens.append({"start": start, "end": end, "text": text[start:end]})
    return tokens


def tag_tokens(tokens, entities):
    tags = ["O"] * len(tokens)
    for entity in entities:
        indexes = [i for i, token in enumerate(tokens) if token["start"] < entity["end"] and entity["start"] < token["end"]]
        if (not indexes or tokens[indexes[0]]["start"] != entity["start"] or tokens[indexes[-1]]["end"] != entity["end"]
                or any(tokens[i]["start"] < entity["start"] or tokens[i]["end"] > entity["end"] for i in indexes)):
            raise ValueError("Entity is not an exact token span")
        for offset, index in enumerate(indexes):
            if tags[index] != "O":
                raise ValueError("Overlapping BIO spans")
            tags[index] = ("B-" if offset == 0 else "I-") + entity["label"]
    return tags


def template_proxy(row):
    text = row["text"]
    for entity in sorted(row["entities"], key=lambda x: x["start"], reverse=True):
        text = text[:entity["start"]] + " <" + entity["label"] + "> " + text[entity["end"]:]
    text = normalize(text)
    text = re.sub(r"\d+(?:[.,:/\-'’]\d+)*", " NUM ", text)
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode()).hexdigest()


def business_candidates(party, businesses):
    if not party:
        return []
    value = " " + normalize(party) + " "
    return sorted(row["businessId"] for row in businesses
                  if any(" " + normalize(form) + " " in value for form in [row["name"]] + row["aliases"]))


def build_groups(rows, businesses, assignments, families, include_topics=False):
    """Conservative transitive closure, never provider-local partitioning."""
    parent, seen = list(range(len(rows))), {}
    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index
    family_by_business = defaultdict(set)
    for family in families:
        for business in businesses:
            if any(normalize(form) == normalize(member) for form in [business["name"]] + business["aliases"] for member in family["members"]):
                family_by_business[business["businessId"]].add(family["familyId"])
    for i, row in enumerate(rows):
        party = next((entity["text"] for entity in row["entities"] if entity["label"] == "MERCHANT"), None)
        ids = business_candidates(party, businesses)
        row["businessMentionCandidates"] = [{"businessId": key, "reservedFold": assignments[key], "evidence": "annotated-party lexical candidate; bounded alias coverage"} for key in ids]
        keys = ["template-proxy:" + template_proxy(row)]
        if include_topics:
            keys.append("source-topic:" + row["sourceCategory"])
        if party:
            keys.append("party:" + normalize(party))
        keys += ["business:" + key for key in ids]
        keys += ["family:" + family for key in ids for family in family_by_business[key]]
        row["groupingKeys"] = sorted(set(keys))
        for key in row["groupingKeys"]:
            if key in seen:
                parent[find(i)] = find(seen[key])
            else:
                seen[key] = i
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[find(i)].append(row)
    result = []
    for members in groups.values():
        ids = sorted(row["id"] for row in members)
        reasons = []
        if any(not row["annotationComplete"] for row in members):
            reasons.append("unresolved_annotation")
        if any(item["reservedFold"] in ("validation", "test") for row in members for item in row["businessMentionCandidates"]):
            reasons.append("protected_merchant_category_identity")
        result.append({"groupId": "bio-group-" + hashlib.sha256("\n".join(ids).encode()).hexdigest()[:16],
                       "recordIds": ids, "quarantineReasons": reasons})
    return sorted(result, key=lambda group: group["groupId"])


def make_split(rows, groups, dataset_hash):
    eligible = [group for group in groups if not group["quarantineReasons"]]
    if len(eligible) < 2:
        return {"splitVersion": "2.0.0", "status": "blocked", "datasetSha256": dataset_hash,
                "reason": "Fewer than two eligible connected groups", "groups": groups}
    # Choose whole components nearest the requested fraction, not a metric-
    # selected row subset. Dynamic programming avoids exponential enumeration.
    choices = {0: ()}
    for index, group in enumerate(eligible):
        for count, selected in list(choices.items()):
            choices.setdefault(count + len(group["recordIds"]), selected + (index,))
    total = sum(len(group["recordIds"]) for group in eligible)
    desired = total * .2
    count = min((n for n in choices if 0 < n < total), key=lambda n: (abs(n - desired), n))
    selected = set(choices[count])
    train = sorted(record for i, group in enumerate(eligible) if i not in selected for record in group["recordIds"])
    validation = sorted(record for i, group in enumerate(eligible) if i in selected for record in group["recordIds"])
    quarantine = sorted(record for group in groups if group["quarantineReasons"] for record in group["recordIds"])
    return {"splitVersion": "2.0.0", "status": "prepared_development_only", "datasetSha256": dataset_hash,
            "validationFractionTarget": .2, "validationFractionActual": len(validation) / (len(train) + len(validation)),
            "trainIds": train, "validationIds": validation, "quarantinedIds": quarantine, "groups": groups,
            "sourceFamiliesIndependentlyVerified": False, "independentEvaluationEligible": False,
            "limits": "Source categories and slot/numeric templates are conservative proxies; alias/family registry is bounded; usable corpus is small and selective"}


def validate_artifacts(artifact, split):
    rows = artifact["examples"]
    by_id = {row["id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("Duplicate BIO record ID")
    for row in rows:
        if row["tokenOffsets"] != [{"start": token["start"], "end": token["end"]} for token in source_tokens(row["text"])]:
            raise ValueError("BIO tokenization must be independent of entity labels")
        tokens = [{**offset, "text": token} for offset, token in zip(row["tokenOffsets"], row["tokens"])]
        if len(row["tokens"]) != len(row["tokenOffsets"]) or len(row["tags"]) != len(tokens):
            raise ValueError("BIO token/tag/offset length mismatch")
        if any(row["text"][token["start"]:token["end"]] != token["text"] for token in tokens):
            raise ValueError("BIO token does not round-trip through source offsets")
        if tag_tokens(tokens, row["entities"]) != row["tags"]:
            raise ValueError("BIO tags do not encode the declared spans")
    if split["status"] == "blocked":
        return
    fold_lists = [split[key] for key in ("trainIds", "validationIds", "quarantinedIds")]
    folds = [set(fold) for fold in fold_lists]
    if any(len(items) != len(unique) for items, unique in zip(fold_lists, folds)):
        raise ValueError("Duplicate record in BIO fold")
    if (not folds[0] or not folds[1] or set.union(*folds) != set(by_id)
            or sum(map(len, folds)) != len(by_id)):
        raise ValueError("BIO folds must cover every record exactly once")
    grouping_keys = []
    for fold in folds[:2]:
        keys = set()
        for key in fold:
            row = by_id[key]
            if not row["annotationComplete"] or any(item["reservedFold"] in ("validation", "test") for item in row["businessMentionCandidates"]):
                raise ValueError("Unreviewed annotation or protected identity admitted to research")
            keys.update(row["groupingKeys"])
        grouping_keys.append(keys)
    if grouping_keys[0] & grouping_keys[1]:
        raise ValueError("BIO template/identity keys cross train and validation")
    grouped_ids = [key for group in split["groups"] for key in group["recordIds"]]
    if len(grouped_ids) != len(by_id) or set(grouped_ids) != set(by_id):
        raise ValueError("BIO groups must cover every record exactly once")
    for group in split["groups"]:
        if group["quarantineReasons"] and not set(group["recordIds"]) <= folds[2]:
            raise ValueError("Quarantined group admitted to a research fold")
        if not any(set(group["recordIds"]) <= fold for fold in folds):
            raise ValueError("Connected BIO group was split")


def build():
    original = json.loads(BIO.read_text(encoding="utf-8"))
    cases = {row["id"]: row for row in json.loads((FIXTURES / "test_suite_cases.json").read_text(encoding="utf-8"))["testCases"]}
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    if review["sourceBioSha256"] != sha256(BIO) or review["sourceFixtureSha256"] != sha256(FIXTURES / "test_suite_cases.json"):
        raise ValueError("Label review does not identify these frozen sources")
    if sha256(RESERVATION) != RESERVATION_HASH:
        raise ValueError("Protected merchant reservation changed")
    replacements = {row["recordId"]: row for row in review["merchantSpanCorrections"]}
    needs_review = {row["recordId"]: row["reason"] for row in review["needsReview"]}
    absent_merchants = {row["recordId"] for row in review["merchantAbsenceReviews"]}
    absent_balances = {row["recordId"] for row in review["balanceAbsenceReviews"]}
    rows, changes = [], []
    for original_row in original["examples"]:
        row = copy.deepcopy(original_row)
        source = cases[row["id"]]
        if row["text"] != source["body"]:
            raise ValueError("BIO text differs from source fixture")
        entities = row["entities"]
        for entity in entities:
            if row["text"][entity["start"]:entity["end"]] != entity["text"]:
                raise ValueError("Legacy source span changed")
            before = dict(entity)
            if entity["label"] == "ACCT" and re.match(r"ending\s", entity["text"], re.I):
                tail = re.search(r"[0-9]{4}$", entity["text"])
                if not tail:
                    raise ValueError("Unrecognized ending account annotation")
                entity["start"] += tail.start()
                entity["text"] = row["text"][entity["start"]:entity["end"]]
            if entity["label"] == "MERCHANT" and row["id"] in replacements:
                replacement = replacements[row["id"]]
                if hashlib.sha256(row["text"].encode()).hexdigest() != replacement["sourceTextSha256"]:
                    raise ValueError("Merchant correction source changed")
                entity.update({key: replacement[key] for key in ("start", "end", "text")})
            if before != entity:
                changes.append({"recordId": row["id"], "label": entity["label"], "before": before, "after": dict(entity), "reviewerType": "assistant"})
            if not 0 <= entity["start"] < entity["end"] <= len(row["text"]) or row["text"][entity["start"]:entity["end"]] != entity["text"]:
                raise ValueError("Corrected entity is not its claimed exact source span")
            if entity["label"] in ("AMT", "BAL"):
                expected = source["expected"]["amount" if entity["label"] == "AMT" else "balance"]
                if Decimal(str(MasroofEngine.parse_number(entity["text"]))) != Decimal(str(expected)):
                    raise ValueError("Numeric annotation differs from the frozen expected value")
        tokens = source_tokens(row["text"])
        row["tokens"] = [token["text"] for token in tokens]
        row["tokenOffsets"] = [{"start": token["start"], "end": token["end"]} for token in tokens]
        row["tags"] = tag_tokens(tokens, entities)
        row["expectedFields"] = copy.deepcopy(source["expected"])
        account = next((entity["text"] for entity in entities if entity["label"] == "ACCT"), None)
        if account is not None:
            row["expectedFields"]["accountMask"] = normalize_financial_numbers(account)
        if row["id"] in replacements:
            row["expectedFields"]["merchantOrParty"] = replacements[row["id"]]["text"]
        reasons = [needs_review[row["id"]]] if row["id"] in needs_review else []
        if source["expected"].get("merchantOrParty") is None and row["id"] not in absent_merchants and row["id"] not in needs_review:
            reasons.append("Unreviewed missing merchant annotation")
        if source["expected"].get("balance") is None and row["id"] not in absent_balances:
            reasons.append("Unreviewed missing balance annotation")
        if source["expected"].get("accountMask") is None:
            normalized = EntityText(row["text"]).text
            if (MasroofEngine.RE_ACC_MASK.search(normalized)
                    or re.search(r'(?:account|card|acc\.?|حساب(?:ك|كم)?|بطاقتك)\s*(?:no\.?\s*)?[0-9]{4,}', normalized, re.I)):
                reasons.append("Possible unannotated account/card identifier")
        field_labels = {"AMT": "amount", "CURR": "currency", "MERCHANT": "merchantOrParty", "ACCT": "accountMask", "BAL": "balance"}
        present = {entity["label"] for entity in entities}
        for label, field in field_labels.items():
            if row["expectedFields"].get(field) is not None and label not in present:
                reasons.append("Missing expected " + label + " span")
        row.update(annotationComplete=not reasons, annotationReviewReasons=reasons, labelOrigin="assistant_policy_corrected_synthetic_development",
                   humanReviewed=False, independentEvaluationEligible=False)
        rows.append(row)
    businesses = [json.loads(line) for line in BUSINESSES.read_text(encoding="utf-8").splitlines() if line.strip()]
    assignments = json.loads(RESERVATION.read_text(encoding="utf-8"))["businessAssignments"]
    families = json.loads(FAMILIES.read_text(encoding="utf-8"))["families"]
    groups = build_groups(rows, businesses, assignments, families)
    # Topic labels intentionally remain a sensitivity audit. Equating all
    # purchases with a single source template would manufacture data starvation.
    topic_groups = build_groups(copy.deepcopy(rows), businesses, assignments, families, include_topics=True)
    sources = [BIO, FIXTURES / "test_suite_cases.json", REVIEW, POLICY, BUSINESSES, RESERVATION, FAMILIES,
               Path(__file__), ROOT / "training/entities/perceptron.py",
               ROOT / "src/python/entity_text.py", ROOT / "src/python/preprocessing.py", ROOT / "src/python/research/bio_sequence.py",
               ROOT / "src/python/engine.py", ROOT / "training/corpus_io.py"]
    inputs = {path.relative_to(ROOT).as_posix(): sha256(path) for path in sources}
    artifact = {"metadata": {"annotationVersion": "2.0.0", "recordCount": len(rows), "inputSha256": inputs,
                             "labelOrigin": "assistant_policy_corrected_existing_synthetic_records", "humanReviewed": False,
                             "independentEvaluationEligible": False, "frozenSourceTextsAndMembershipUnchanged": True}, "examples": rows}
    data_text = json_text(artifact)
    split = make_split(rows, groups, hashlib.sha256(data_text.encode()).hexdigest())
    validate_artifacts(artifact, split)
    old_train, old_validation, _ = split_examples(original["examples"])
    old_folds = {row["id"]: fold for fold, examples in (("train", old_train), ("validation", old_validation)) for row in examples}
    crossing = [group for group in groups if len({old_folds[key] for key in group["recordIds"]}) > 1]
    vocabulary = {normalize_token(token) for row in old_train for token in row["tokens"]}
    tag_total, unseen = Counter(), Counter()
    for row in old_validation:
        for token, tag in zip(row["tokens"], row["tags"]):
            tag_total[tag] += 1
            unseen[tag] += normalize_token(token) not in vocabulary
    report = {"version": "2.0.0", "scope": "BIO policy correction and split audit; no model fitting or independent accuracy",
              "inputSha256": inputs, "recordCount": len(rows), "changedEntitySpans": changes,
              "artifactSha256": {DATA.relative_to(ROOT).as_posix(): hashlib.sha256(data_text.encode()).hexdigest(),
                                 SPLIT.relative_to(ROOT).as_posix(): hashlib.sha256(json_text(split).encode()).hexdigest()},
              "unresolvedAnnotationRecords": [{"id": row["id"], "reasons": row["annotationReviewReasons"]} for row in rows if not row["annotationComplete"]],
              "oldSplit": {"train": len(old_train), "validation": len(old_validation), "jointGroupsCrossingFolds": len(crossing),
                           "recordsInCrossingGroups": len({key for group in crossing for key in group["recordIds"]})},
              "oldValidationTokenCoverage": {tag: {"total": tag_total[tag], "unseen": unseen[tag]} for tag in sorted(tag_total)},
              "topicGroupingSensitivity": {"note": "Source topics are not verified template families; this conservative stress grouping is not the selected split",
                                           "groupSizes": sorted((len(group["recordIds"]) for group in topic_groups), reverse=True)},
              "newSplit": {"status": split["status"], "groupSizes": sorted((len(group["recordIds"]) for group in groups), reverse=True),
                           "train": len(split.get("trainIds", [])), "validation": len(split.get("validationIds", [])), "quarantined": len(split.get("quarantinedIds", [])),
                           "quarantineReasons": dict(Counter(reason for group in groups for reason in group["quarantineReasons"]))},
              "currencyAliasesAreNotAnnotationErrors": True, "modelFitted": False, "activeDataOrWeightsChanged": False,
              "limits": ["Assistant review is not human gold; all records remain synthetic development-exposed.", "Known business/alias grouping is bounded, not verified exhaustive identity resolution.", "Quarantine preserves the existing merchant-category reservation; no test-identity fitting or inference.", "Current word-only tagger can memorize numeric tokens; richer features require a separate reviewed model change."]}
    return {DATA: data_text, SPLIT: json_text(split), REPORT: json_text(report)}, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    outputs, report = build()
    if not args.preview:
        if not args.check:
            snapshot_report_inputs("bio_annotations_v2", report["inputSha256"])
        for path, content in outputs.items():
            if args.check:
                if not path.exists() or path.read_text(encoding="utf-8") != content:
                    raise ValueError("BIO artifact missing or stale: " + str(path))
            else:
                write_immutable(path, content)
    print(json_text({"records": report["recordCount"], "spanCorrections": len(report["changedEntitySpans"]),
                     "unresolved": len(report["unresolvedAnnotationRecords"]), "oldSplit": report["oldSplit"], "newSplit": report["newSplit"]}))


if __name__ == "__main__":
    main()
