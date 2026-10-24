"""Reserve prospective business holdouts; never manufacture independent SMS."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training.build_business_shortlist import normalize

BUSINESSES = ROOT / "data/annotations/businesses_200.jsonl"
PLAN = ROOT / "data/training/splits/category_brand_split.json"
REPORT = ROOT / "data/reports/category_evaluation_readiness.json"
ARABIC = re.compile(r"[\u0621-\u064a]")
SEED = "masroof-jordan-category-holdout-v1"
FOLDS = ("train", "validation", "test")


def identity_groups(rows: list[dict]) -> dict[str, str]:
    """Pool shared identities and conservatively reserve prefix-related names."""
    ids = [row["businessId"] for row in rows]
    if len(set(ids)) != len(ids) or not rows:
        raise ValueError("Expected non-empty distinct business identities")
    parent = {key: key for key in ids}

    def find(key):
        while parent[key] != key:
            key = parent[key]
        return key

    def union(left, right):
        a, b = sorted((find(left), find(right)))
        parent[b] = a

    alias_owners = {}
    for row in rows:
        if not row.get("brandGroup"):
            raise ValueError("Business missing brand group")
        for name in [row["name"]] + row["aliases"]:
            key = normalize(name)
            if not key:
                raise ValueError("Empty business name or alias")
            if key in alias_owners:
                union(row["businessId"], alias_owners[key])
            alias_owners[key] = row["businessId"]
    for i, left in enumerate(rows):
        for right in rows[i + 1:]:
            a, b = sorted((re.findall(r"\w+", left["name"].casefold()), re.findall(r"\w+", right["name"].casefold())), key=len)
            # A conservative anti-leakage bucket, not a claim of corporate ownership.
            if left["brandGroup"] == right["brandGroup"] or (len("".join(a)) >= 4 and b[:len(a)] == a):
                union(left["businessId"], right["businessId"])
    return {key: find(key) for key in ids}


def prepare(rows: list[dict], previous: dict | None = None) -> dict:
    groups = identity_groups(rows)
    buckets = {}
    for row in rows:
        buckets.setdefault(groups[row["businessId"]], []).append(row)
    if previous is not None:
        if previous.get("version") != "1.0.0" or previous.get("seed") != SEED:
            raise ValueError("Unsupported existing split contract")
        assignments = previous["businessAssignments"]
        if set(assignments) != set(groups) or any(fold not in FOLDS for fold in assignments.values()):
            raise ValueError("Business membership changed; explicitly review the split instead of reshuffling")
        for members in buckets.values():
            if len({assignments[row["businessId"]] for row in members}) != 1:
                raise ValueError("New alias/family evidence crosses frozen folds; review before proceeding")
    else:
        assignments = {}
        for has_arabic in (False, True):
            eligible = [key for key, members in buckets.items()
                        if any(ARABIC.search(name) for row in members for name in [row["name"]] + row["aliases"]) == has_arabic]
            eligible.sort(key=lambda key: hashlib.sha256(f"{SEED}:{key}".encode()).hexdigest())
            heldout_count = round(len(eligible) * 0.15)
            for index, key in enumerate(eligible):
                fold = "test" if index < heldout_count else "validation" if index < 2 * heldout_count else "train"
                for row in buckets[key]:
                    assignments[row["businessId"]] = fold
    return {
        "version": "1.0.0", "seed": SEED, "geographicScope": "Jordan",
        "scope": "Prospective merchant-metadata holdout reservation; not independent real SMS or measured accuracy.",
        "method": "Hash-sort groups within Arabic-name-available / other strata; reserve 15% each for validation and test, remainder training. Existing assignments are frozen on rebuild. No category labels used for allocation.",
        "grouping": "Existing brand groups, exact normalized name/alias overlap, and conservative whole-token canonical-name prefix overlap containing at least four characters. Prefix grouping prevents possible leakage and does not assert common ownership. Audit unrelated-looking names with common ownership before training.",
        "businessAssignments": dict(sorted(assignments.items())),
        "leakageGroups": {key: sorted(row["businessId"] for row in members) for key, members in sorted(buckets.items())},
    }


def readiness(rows: list[dict], plan: dict, allowed: list[str]) -> dict:
    folds = {}
    for fold in FOLDS:
        selected = [row for row in rows if plan["businessAssignments"][row["businessId"]] == fold]
        reviewed = [row for row in selected if row["labelStatus"] == "human_reviewed_merchant_default"
                    and row["humanConfirmedCategory"] in allowed]
        counts = Counter(row["humanConfirmedCategory"] for row in reviewed)
        folds[fold] = {
            "businessCount": len(selected),
            "leakageGroupCount": sum(any(key in {row['businessId'] for row in selected} for key in members) for members in plan["leakageGroups"].values()),
            "businessesWithArabicNameOrAlias": sum(any(ARABIC.search(name) for name in [row["name"]] + row["aliases"]) for row in selected),
            "humanReviewedMerchantDefaults": len(reviewed),
            "assistantReviewedMerchantDefaults": sum(row["labelStatus"] == "assistant_reviewed_merchant_default" and row.get("assistantReviewedCategory") in allowed for row in selected),
            "reviewedCategoryCounts": dict(sorted(counts.items())),
            "categoriesWithoutReviewedExamples": [category for category in allowed if not counts[category]],
        }
    return {
        "version": "1.0.0", "geographicScope": "Jordan", "folds": folds,
        "businessCorpusSha256": hashlib.sha256(BUSINESSES.read_bytes()).hexdigest(),
        "categoryModelReady": False, "independentSmsEvaluationReady": False,
        "accuracy": None,
        "limitations": [
            "This reserves metadata identities only. No independent SMS set was collected or validated by this script.",
            "Frozen regression messages were used in development; numeral transformations and authored boundary scenarios cannot become independent test evidence.",
            "Human labels here are merchant defaults, not transaction-context labels. Source proposals and aliases are not new gold examples.",
            "User-authorized assistant reviews are separate research labels, not independent human gold. Do not score category accuracy against the assistant's own judgments.",
            "All names and aliases of held-out businesses are forbidden in model fitting, augmentation, vocabulary/feature selection and calibration. Validation is for tuning; test is for final evaluation.",
            "Existing human labels and public listings were visible during research; this is a prospective holdout, not a blind external benchmark.",
            "Cash Withdrawals, Fees and Installments need transaction-context data; merchant-name coverage cannot establish readiness for all 15 categories.",
        ],
        "requiredNext": ["Resolve remaining ambiguous merchant labels without fitting against held-out results.",
                         "Acquire independently sourced, sanitized Jordanian Arabic bank/wallet SMS with provenance and human-reviewed transaction, amount, direction and category labels; do not generate substitutes.",
                         "Audit source/template and business overlap with existing training and frozen regression fixtures before admitting SMS to evaluation.",
                         "Before category training, audit remaining related-brand families, then use only train assignments; report business-level English/Arabic metrics and context-required abstentions separately."],
    }


def main():
    rows = [json.loads(line) for line in BUSINESSES.read_text(encoding="utf-8").splitlines() if line.strip()]
    previous = json.loads(PLAN.read_text(encoding="utf-8")) if PLAN.exists() else None
    plan = prepare(rows, previous)
    allowed = json.loads((ROOT / "data/annotations/category_annotation_schema.json").read_text(encoding="utf-8"))["allowedCategories"]
    report = readiness(rows, plan, allowed)
    for path, payload in ((PLAN, plan), (REPORT, report)):
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"folds": report["folds"], "accuracy": None, "independentSmsEvaluationReady": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
