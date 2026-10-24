"""Audit category coverage and known leakage without moving frozen assignments."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training.prepare_category_evaluation import FOLDS, prepare
from training.build_business_shortlist import normalize
from src.python.preprocessing import preprocess_message, PREPROCESSING_CONTRACT_VERSION

BUSINESSES = ROOT / "data/annotations/businesses_200.jsonl"
SPLIT = ROOT / "data/training/splits/category_brand_split.json"
FAMILIES = ROOT / "data/sources/businesses/brand_families.json"
REPORT = ROOT / "data/reports/category_corpus_audit.json"
READABLE = ROOT / "data/reports/CATEGORY_CORPUS_AUDIT.md"
TAXONOMY = ROOT / "data/annotations/category_annotation_schema.json"


def label(row):
    if row["labelStatus"] == "human_reviewed_merchant_default":
        return row["humanConfirmedCategory"], "human"
    if row["labelStatus"] == "assistant_reviewed_merchant_default":
        return row["assistantReviewedCategory"], "assistant"
    return None, None


def audit(rows: list[dict], plan: dict, allowed: list[str], families: list[dict]) -> dict:
    # Reuse the split validator; never silently repair allocations for an audit.
    prepare(rows, plan)
    if len(set(allowed)) != len(allowed):
        raise ValueError("Duplicate category contract labels")
    by_name = {row["name"]: row for row in rows}
    fold_counts = {}
    owners = {"identity": defaultdict(set), "preprocessing": defaultdict(set)}
    raw_forms = set()
    for row in rows:
        category, _ = label(row)
        if row["labelStatus"] not in {"needs_review", "human_reviewed_merchant_default", "assistant_reviewed_merchant_default"}:
            raise ValueError("Unsupported label provenance")
        if category is not None and category not in allowed:
            raise ValueError(f"Unsupported reviewed category: {category}")
        if row["labelStatus"] != "needs_review" and category is None:
            raise ValueError("Reviewed business has no category")
        for name in [row["name"]] + row["aliases"]:
            raw_forms.add(name)
            owners["identity"][normalize(name)].add(row["businessId"])
            owners["preprocessing"][preprocess_message(name)].add(row["businessId"])
    for fold in FOLDS:
        selected = [row for row in rows if plan["businessAssignments"][row["businessId"]] == fold]
        counts = {kind: Counter() for kind in ("human", "assistant", "combined")}
        for row in selected:
            category, kind = label(row)
            if category is not None:
                counts[kind][category] += 1
                counts["combined"][category] += 1
        fold_counts[fold] = {
            "businessCount": len(selected), "labeledBusinesses": sum(counts["combined"].values()),
            "categoryCounts": {kind: {category: counts[kind][category] for category in allowed} for kind in counts},
            "categoriesWithoutTrainingOrEvaluationLabels": [category for category in allowed if not counts["combined"][category]],
            "arabicNameOrAliasBusinessCount": sum(any(re.search(r"[\u0621-\u064a]", name) for name in [row["name"]] + row["aliases"]) for row in selected),
        }
    collisions = {}
    for kind, mapping in owners.items():
        collisions[kind] = [{"form": form, "businessIds": sorted(ids),
                             "folds": sorted({plan["businessAssignments"][key] for key in ids})}
                            for form, ids in sorted(mapping.items()) if len(ids) > 1]
    family_checks = []
    for family in families:
        members = family["members"]
        if not members or len(set(members)) != len(members) or any(name not in by_name for name in members):
            raise ValueError("Family references unknown/duplicate identities")
        if not family.get("url", "").startswith("https://") or not family.get("evidence"):
            raise ValueError("Family evidence is required")
        folds = sorted({plan["businessAssignments"][by_name[name]["businessId"]] for name in members})
        family_checks.append({"familyId": family["familyId"], "members": members,
                              "folds": folds, "crossFold": len(folds) > 1, "sourceUrl": family["url"]})
    missing = fold_counts["train"]["categoriesWithoutTrainingOrEvaluationLabels"]
    return {
        "version": "1.0.0", "geographicScope": "Jordan", "preprocessingVersion": PREPROCESSING_CONTRACT_VERSION,
        "scope": "Merchant metadata only; exhaustive exact-form checks and bounded known-family evidence, not proof of unseen SMS generalization.",
        "businessCount": len(rows), "labeledBusinesses": sum(label(row)[0] is not None for row in rows),
        "unresolvedBusinesses": [row["name"] for row in rows if label(row)[0] is None],
        "distinctRawNameForms": len(raw_forms), "distinctIdentityNormalizedForms": len(owners["identity"]),
        "distinctPreprocessedForms": len(owners["preprocessing"]),
        "folds": fold_counts, "crossBusinessFormCollisions": collisions,
        "verifiedFamilyChecks": family_checks,
        "exactFormCrossFoldConflicts": sum(len(item["folds"]) > 1 for items in collisions.values() for item in items),
        "knownFamilyCrossFoldConflicts": sum(item["crossFold"] for item in family_checks),
        "missingTrainingCategories": missing,
        "evaluationOnlyCategories": {fold: [category for category in missing if fold_counts[fold]["categoryCounts"]["combined"][category]] for fold in ("validation", "test")},
        "sparseTrainingCategories": {category: count for category, count in fold_counts["train"]["categoryCounts"]["combined"].items() if 0 < count < 3},
        "allTargetCategoriesRepresentedInTraining": not missing,
        "full15CategoryTrainingReady": False,
        "augmentationPolicy": {
            "status": "bounded_training_protocol_run_status_in_merchant_category_research_report",
            "firstExperiment": "Compare unchanged names against source-observed training aliases, then at most one feature-changing format/noise variant per eligible training business.",
            "trainingBusinessLimit": fold_counts["train"]["labeledBusinesses"],
            "maxSyntheticExtraFormsPerTrainingBusiness": 1,
            "sampling": "Keep each business's total weight equal; variants are not new businesses or new human labels.",
            "rules": ["Generate only after frozen fold assignment; retain businessId, family, base record and reviewer type.",
                      "Never augment validation/test or the two unresolved identities; filter candidate forms against all held-out names and aliases before accepting them.",
                      "Deduplicate through the exact model preprocessing/features; casing, diacritics and digit variants already canonicalized are not new model evidence.",
                      "Source-observed Arabic/English aliases are preferred. Do not invent transliterations or merchant identities; record synthetic provenance for generated text.",
                      "Do not add category words such as restaurant to opaque names just because that is the label; this would leak the answer.",
                      "For future SMS augmentation protect negation, completion/decline/OTP cues, amount, currency, direction and entity spans; merchant defaults do not label every purchase.",
                      "A/B compare no-augmentation versus augmentation on unchanged validation businesses; keep test sealed until final evaluation.",
                      "Augmentation does not create missing categories, independent labels, source diversity or new unseen merchants."],
        },
        "limitations": ["Family evidence is bounded, not an exhaustive parent/franchise ownership audit.",
                        "Template/source separation is not established by this name-only audit; historical SMS exposure is reported as lexical candidates only.",
                        "Assistant-reviewed labels are research supervision. Human evaluation is sparse; never call agreement with the same assistant independent accuracy.",
                        "Only three Arabic-name businesses are reserved per validation/test fold; results would be small-sample diagnostics.",
                        "A merchant-only research candidate may cover supported classes with abstention; this corpus cannot establish a full 15-category SMS classifier."],
    }


def words(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    return tuple(re.findall(r"[^\W_]+", re.sub(r"[\u064b-\u065f\u0670]", "", text)))


def historical_mentions(rows: list[dict], plan: dict, corpora: dict[str, list[dict]]) -> dict:
    """Flag exact token-sequence mentions; a matching name is not identity proof."""
    names = {}
    for row in rows:
        if plan["businessAssignments"][row["businessId"]] != "train":
            names[row["businessId"]] = {words(name) for name in [row["name"]] + row["aliases"] if words(name)}
    reports = {}
    for source, records in corpora.items():
        found = defaultdict(list)
        for index, record in enumerate(records):
            tokens = words(record.get("text", record.get("body", "")))
            for key, forms in names.items():
                if any(any(tokens[i:i + len(form)] == form for i in range(len(tokens) - len(form) + 1)) for form in forms):
                    found[key].append(record.get("id", f"row-{index}"))
        reports[source] = {"matchingRecordCount": len({key for ids in found.values() for key in ids}),
                           "potentialHeldoutBusinessMentions": dict(sorted(found.items()))}
    return {"scope": "Lexical candidates in legacy training/regression only; generic words can match unrelated businesses. Not a template-similarity audit or evidence that a new name-only candidate used these records.", "corpora": reports}


def main():
    rows = [json.loads(line) for line in BUSINESSES.read_text(encoding="utf-8").splitlines()]
    plan = json.loads(SPLIT.read_text(encoding="utf-8"))
    allowed = json.loads(TAXONOMY.read_text(encoding="utf-8"))["allowedCategories"]
    report = audit(rows, plan, allowed, json.loads(FAMILIES.read_text(encoding="utf-8"))["families"])
    paths = [ROOT / "data/training/dataset_expanded.json", ROOT / "tests/fixtures/test_suite_cases.json", ROOT / "tests/fixtures/qa_adversarial_cases.json"]
    corpora = {}
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        corpora[str(path.relative_to(ROOT))] = payload if isinstance(payload, list) else payload["testCases"]
    report["historicalSmsExposure"] = historical_mentions(rows, plan, corpora)
    report["inputSha256"] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in [BUSINESSES, SPLIT, FAMILIES, TAXONOMY] + paths}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Jordan merchant-category corpus audit", "", "Metadata audit, not a model evaluation. All counts are distinct businesses; aliases do not increase sample size.", "",
             "| Category | Train human | Train assistant | Train total | Validation total | Test total |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for category in allowed:
        train = report["folds"]["train"]["categoryCounts"]
        lines.append(f"| {category} | {train['human'][category]} | {train['assistant'][category]} | {train['combined'][category]} | {report['folds']['validation']['categoryCounts']['combined'][category]} | {report['folds']['test']['categoryCounts']['combined'][category]} |")
    lines += ["", "Missing training categories: " + ", ".join(report["missingTrainingCategories"]) + ".", "",
              f"Cross-fold exact-form conflicts: {report['exactFormCrossFoldConflicts']}. Verified-family cross-fold conflicts: {report['knownFamilyCrossFoldConflicts']}. Family coverage is bounded, not exhaustive.", "",
              "Known family: Inditex (Lefties, Massimo Dutti, Oysho, Stradivarius, ZARA, ZARA Home), all in training. Source: https://annualreport.inditex.com/anrpxxvui/en/our-drivers", "",
              "Historical SMS mentions and input hashes are in category_corpus_audit.json. Generic names may produce false identity matches. Do not mix legacy SMS into new fitting data without auditing its held-out business and template overlap.", "",
              "Bounded augmentation protocol: begin with observed training aliases, then at most one feature-changing synthetic variant per training business; keep equal business weight and untouched holdouts. It cannot create missing categories or independent test truth. This audit does not train models; see merchant_category_research.json for experiment status.", "",
              "Research basis: [EDA text augmentation paper](https://aclanthology.org/D19-1670/) and [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html). These do not establish effectiveness for Jordanian SMS; use a controlled local A/B experiment."]
    READABLE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("labeledBusinesses", "missingTrainingCategories", "evaluationOnlyCategories", "sparseTrainingCategories", "exactFormCrossFoldConflicts", "knownFamilyCrossFoldConflicts")}, ensure_ascii=False, indent=2))
    print(json.dumps({key: value["matchingRecordCount"] for key, value in report["historicalSmsExposure"]["corpora"].items()}, indent=2))


if __name__ == "__main__":
    main()
