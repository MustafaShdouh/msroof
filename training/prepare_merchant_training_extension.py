"""Validate sourced training-only additions without changing the reserved 200."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.python.merchant_category import normalize_name, name_features
from training.build_business_shortlist import normalize
from training.prepare_category_evaluation import prepare
from training.audit_category_corpus import label

SOURCE = ROOT / "data/sources/businesses/jordan_training_extension.json"
BASE = ROOT / "data/annotations/businesses_200.jsonl"
SPLIT = ROOT / "data/training/splits/category_brand_split.json"
TAXONOMY = ROOT / "data/annotations/category_annotation_schema.json"
OUTPUT = ROOT / "data/annotations/merchant_training_extension.jsonl"
REPORT = ROOT / "data/reports/merchant_training_extension_audit.json"
CONTEXT_ONLY = {"Cash Withdrawals", "Installments", "Fees"}


def validate_extension(records, base, plan, allowed):
    prepare(base, plan)
    owners, feature_owners, base_names = {}, {}, []
    base_ids = {row["businessId"] for row in base}
    for row in base:
        for name in [row["name"]] + row["aliases"]:
            owners[normalize(name)] = row["businessId"]
            feature_owners[tuple(name_features(name))] = row["businessId"]
            base_names.append((row["businessId"], normalize_name(name).split()))
    result = []
    ids = set()
    for raw in records:
        if raw.get("geographicScope") != "Jordan" or raw.get("reviewerType") != "assistant" or raw.get("status") != "approved" or raw.get("labelScope") != "merchant_name":
            raise ValueError("Extension must be explicit Jordan assistant-reviewed merchant metadata")
        category = raw.get("category")
        if category not in allowed or category in CONTEXT_ONLY:
            raise ValueError("Unsupported or transaction-context-only category for a merchant name")
        name, aliases = raw.get("name"), raw.get("aliases")
        if not isinstance(name, str) or not isinstance(aliases, list) or any(not isinstance(item, str) for item in aliases):
            raise ValueError("Invalid extension name/aliases")
        key = normalize(name)
        if not key:
            raise ValueError("Empty identity")
        business_id = "business-" + hashlib.sha256(key.encode()).hexdigest()[:16]
        if business_id in ids:
            raise ValueError("Duplicate extension identity")
        if not isinstance(raw.get("notes"), str) or not raw["notes"].strip() or not raw.get("reviewer"):
            raise ValueError("Reviewer and rationale required")
        sources = raw.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError("Sources required")
        for source in sources:
            if not isinstance(source, dict) or not isinstance(source.get("url"), str) or not source["url"].startswith("https://") or not all(source.get(field) for field in ("publisher", "accessedOn", "evidence")):
                raise ValueError("Complete HTTPS source provenance required")
        cities = raw.get("cities", [])
        if not isinstance(cities, list) or any(city not in ("Amman", "Irbid") for city in cities):
            raise ValueError("Unsupported city evidence")
        for form in [name] + aliases:
            signature = tuple(name_features(form))
            normalized = normalize(form)
            if not normalized or not signature:
                raise ValueError("Empty alias features")
            if normalized in owners or signature in feature_owners:
                owner = owners.get(normalized, feature_owners.get(signature))
                if owner in base_ids or owner != business_id:
                    raise ValueError("Extension overlaps an existing reserved or extension identity; enrich that identity instead")
            tokens = normalize_name(form).split()
            for owner, original in base_names:
                short, long = sorted((tokens, original), key=len)
                if len("".join(short)) >= 4 and long[:len(short)] == short:
                    raise ValueError("Possible related-brand prefix overlaps reserved corpus; resolve identity before admission")
            owners[normalized] = business_id
            feature_owners[signature] = business_id
        ids.add(business_id)
        result.append({"businessId": business_id, "name": name, "brandGroup": key,
                       "aliases": sorted(set(aliases) - {name}), "cities": sorted(set(cities)),
                       "geographicScope": "Jordan", "datasetScope": "business_metadata_not_bank_sms",
                       "labelStatus": "assistant_reviewed_merchant_default", "humanConfirmedCategory": None,
                       "assistantReviewedCategory": category, "reviewer": raw["reviewer"],
                       "reviewerType": "assistant", "labelScope": "merchant_name", "notes": raw["notes"],
                       "sources": sources, "fold": "train", "evaluationEligible": False,
                       "allocationBasis": "Prospective training-only category coverage collection; original 200-business assignments unchanged.",
                       "estimatedCorrectnessPct": None})
    return sorted(result, key=lambda row: row["businessId"])


def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    base = [json.loads(line) for line in BASE.read_text(encoding="utf-8").splitlines()]
    plan = json.loads(SPLIT.read_text(encoding="utf-8"))
    allowed = json.loads(TAXONOMY.read_text(encoding="utf-8"))["allowedCategories"]
    rows = validate_extension(source["businesses"], base, plan, allowed)
    original = Counter(label(row)[0] for row in base if plan["businessAssignments"][row["businessId"]] == "train" and label(row)[0] is not None)
    additions = Counter(row["assistantReviewedCategory"] for row in rows)
    combined = original + additions
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    report = {"version": "1.0.0", "scope": "Prospective training extension; assistant research labels, not independent SMS truth or new holdout businesses.",
              "extensionBusinessCount": len(rows), "originalBusinessCount": len(base),
              "extensionCategoryCounts": dict(sorted(additions.items())),
              "combinedTrainingCategoryCounts": {category: combined[category] for category in allowed},
              "originalLabeledTrainingBusinesses": sum(original.values()), "combinedLabeledTrainingBusinesses": sum(combined.values()),
              "combinedRepresentedTrainingCategories": sum(combined[category] > 0 for category in allowed),
              "missingTrainingCategories": [category for category in allowed if not combined[category]],
              "extensionArabicNameOrAliasBusinesses": sum(any(re.search(r"[\u0621-\u064a]", name) for name in [row["name"]] + row["aliases"]) for row in rows),
              "inputSha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (SOURCE, BASE, SPLIT, TAXONOMY)},
              "outputSha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
              "limitations": ["Do not concatenate these into the original 200-business shortlist or reshuffle holdouts.",
                              "No model was trained by this preparation step. Existing v1 exports/reports remain historical snapshots.",
                              "Exact names/features and conservative whole-token prefixes were checked; this is not an exhaustive corporate ownership audit.",
                              "Digital subscriptions have Jordan service availability evidence; no physical Amman/Irbid branch is inferred.",
                              "JoPetrol fuel, Uber rides and bus fares are defaults; household heating, refunds or explicit recurring passes need payment context.",
                              "Source names and assistant category judgments are separate evidence; no measured correctness probability or SMS descriptor coverage is established."]}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("extensionBusinessCount", "extensionCategoryCounts", "combinedLabeledTrainingBusinesses", "combinedRepresentedTrainingCategories", "missingTrainingCategories")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
