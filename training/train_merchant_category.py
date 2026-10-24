"""Deterministic merchant-only research A/B; no SMS or active-model replacement."""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.python.merchant_category import CONTRACT_VERSION, name_features, normalize_name, load_model, predict
from training.audit_category_corpus import audit, label
from training.prepare_category_evaluation import prepare

BUSINESSES = ROOT / "data/annotations/businesses_200.jsonl"
SPLIT = ROOT / "data/training/splits/category_brand_split.json"
TAXONOMY = ROOT / "data/annotations/category_annotation_schema.json"
FAMILIES = ROOT / "data/sources/businesses/brand_families.json"
REPORT = ROOT / "data/reports/merchant_category_research.json"
SEED = 20261024
EPOCHS = 100
LEARNING_RATE = 0.3
L2 = 0.001
VARIANTS = ("baseline", "aliases", "augmented")
POLICY = {"minScore": 0.6, "minMargin": 0.15, "minKnownFeatureFraction": 0.15, "minClassBusinesses": 3}


def synthetic_form(text):
    """One descriptor-spacing change, or a single internal Latin-letter repeat."""
    normalized = normalize_name(text)
    if " " in normalized:
        return normalized.replace(" ", "", 1), "remove_one_word_separator"
    positions = [i for i in range(1, len(normalized) - 1) if 'a' <= normalized[i] <= 'z']
    if len(normalized) >= 5 and positions:
        offset = int(hashlib.sha256(normalized.encode()).hexdigest()[:8], 16) % len(positions)
        i = positions[offset]
        return normalized[:i] + normalized[i] + normalized[i:], "repeat_one_internal_latin_letter"
    return None, None


def training_views(rows, plan, variant):
    if variant not in VARIANTS:
        raise ValueError("Unknown training variant")
    heldout = {tuple(name_features(name)) for row in rows if plan["businessAssignments"][row["businessId"]] != "train"
               for name in [row["name"]] + row["aliases"]}
    result = []
    for row in sorted(rows, key=lambda item: item["businessId"]):
        category, reviewer = label(row)
        if plan["businessAssignments"][row["businessId"]] != "train" or category is None:
            continue
        forms = [(row["name"], "canonical_name")]
        if variant != "baseline":
            forms += [(name, "source_observed_alias") for name in sorted(row["aliases"])]
        if variant == "augmented":
            text, method = synthetic_form(row["name"])
            if text:
                forms.append((text, method))
        unique = {}
        for text, method in forms:
            signature = tuple(name_features(text))
            if not signature:
                continue
            if signature in heldout:
                raise ValueError("Training name/augmentation collides with held-out feature input")
            unique.setdefault(signature, {"text": text, "method": method})
        if not unique:
            raise ValueError("Labeled business has no usable name")
        views = list(unique.values())
        for view in views:
            view.update(businessId=row["businessId"], baseName=row["name"], category=category, labelReviewerType=reviewer,
                        dataKind="synthetic_name_perturbation" if view["method"] not in ("canonical_name", "source_observed_alias") else "source_observed_name",
                        businessWeight=1 / len(views))
        result.append(views)
    return result


def fit(groups, classes, variant, input_hashes):
    features = sorted({feature for group in groups for view in group for feature in name_features(view["text"])})
    index = {feature: i for i, feature in enumerate(features)}
    class_index = {category: i for i, category in enumerate(classes)}
    support = Counter(group[0]["category"] for group in groups)
    encoded = [[([index[feature] for feature in name_features(view["text"])], class_index[view["category"]], view["businessWeight"])
                for view in group] for group in groups]
    count = len(classes)
    weights, bias = [0.0] * (len(features) * count), [0.0] * count
    rng = random.Random(SEED)
    order = list(range(len(groups)))
    for epoch in range(EPOCHS):
        rng.shuffle(order)
        rate = LEARNING_RATE / math.sqrt(1 + epoch / 10)
        shrink = 1 - rate * L2
        weights = [value * shrink for value in weights]
        for business in order:
            for ids, target, business_weight in encoded[business]:
                scale = 1 / math.sqrt(len(ids))
                scores = list(bias)
                for feature in ids:
                    offset = feature * count
                    for c in range(count):
                        scores[c] += weights[offset + c] * scale
                maximum = max(scores)
                exp = [math.exp(value - maximum) for value in scores]
                total = sum(exp)
                updates = [rate * business_weight * ((1 if c == target else 0) - exp[c] / total) for c in range(count)]
                for c in range(count):
                    bias[c] += updates[c]
                for feature in ids:
                    offset = feature * count
                    for c in range(count):
                        weights[offset + c] += updates[c] * scale
    return {
        "contractVersion": CONTRACT_VERSION, "researchOnly": True, "scope": "merchant_name_default_not_transaction_sms",
        "normalization": "NFKC; shared financial digits; lowercase; remove Arabic diacritics/tatweel; retain ASCII digits, Latin U+00C0-024F and Arabic U+0621-064A letters; other runs become one space; trim. No SMS routing-prefix removal.",
        "featureEncoding": "binary_word_unigrams_and_boundary_padded_character_3_4_5grams; sorted; scale by inverse sqrt of known feature count",
        "weightLayout": "feature_major_flat_float64", "classes": classes, "features": features,
        "weights": [round(value, 10) for value in weights], "bias": [round(value, 10) for value in bias],
        "classBusinessSupport": [support[category] for category in classes], "abstention": POLICY,
        "scoreMeaning": "Softmax score is uncalibrated, not a probability of correctness; abstention thresholds are fixed pilot settings.",
        "training": {"version": "1.0.0", "variant": variant, "seed": SEED, "epochs": EPOCHS,
                     "learningRate": LEARNING_RATE, "l2EpochShrink": L2, "inputSha256": input_hashes,
                     "businessCount": len(groups), "viewCount": sum(map(len, groups)),
                     "businessIds": [group[0]["businessId"] for group in groups],
                     "labelSources": dict(Counter(group[0]["labelReviewerType"] for group in groups)),
                     "sampling": "Each business has total view weight one per epoch; variants are not independent observations."},
    }


def summarize(records):
    answered = [row for row in records if row["prediction"]["category"] is not None]
    correct = sum(row["prediction"]["category"] == row["expectedCategory"] for row in answered)
    top_correct = sum(row["prediction"]["topClass"] == row["expectedCategory"] for row in records)
    confusion = Counter((row["expectedCategory"], row["prediction"]["topClass"]) for row in records)
    return {"businessCount": len(records), "answered": len(answered), "correctAnswered": correct,
            "wrongAnswered": len(answered) - correct, "abstained": len(records) - len(answered),
            "coverage": len(answered) / len(records) if records else None,
            "accuracyAmongAnswered": correct / len(answered) if answered else None,
            "top1AccuracyBeforeAbstention": top_correct / len(records) if records else None,
            "correctIncludingAbstentionsAsMisses": correct / len(records) if records else None,
            "top1Confusion": [{"expected": a, "predicted": b, "count": n} for (a, b), n in sorted(confusion.items())]}


def evaluate(model, rows, plan, fold):
    if fold not in ("train", "validation"):
        raise ValueError("Final test inference is deliberately disabled during model development")
    loaded = load_model(model)
    records = []
    arabic_records = []
    for row in rows:
        category, reviewer = label(row)
        if plan["businessAssignments"][row["businessId"]] != fold or category is None:
            continue
        record = {"businessId": row["businessId"], "name": row["name"], "expectedCategory": category,
                  "reviewerType": reviewer, "prediction": predict(loaded, row["name"])}
        records.append(record)
        # One aggregation per business, even when several Arabic aliases exist.
        forms = sorted({normalize_name(name) for name in [row["name"]] + row["aliases"] if any('\u0621' <= char <= '\u064a' for char in name)})
        if forms:
            predictions = [predict(loaded, text) for text in forms]
            arabic_records.append({"businessId": row["businessId"], "reviewerType": reviewer,
                                   "observedFormCount": len(forms),
                                   "allFormsCorrect": all(p["category"] == category for p in predictions),
                                   "allFormsAbstained": all(p["category"] is None for p in predictions)})
    return {"combinedResearchLabels": summarize(records),
            "humanLabelsOnly": summarize([row for row in records if row["reviewerType"] == "human"]),
            "assistantLabelsOnly": summarize([row for row in records if row["reviewerType"] == "assistant"]),
            "arabicObservedNames": {"businessCount": len(arabic_records),
                                    "allFormsCorrect": sum(row["allFormsCorrect"] for row in arabic_records),
                                    "allFormsAbstained": sum(row["allFormsAbstained"] for row in arabic_records),
                                    "records": arabic_records}, "records": records}


def choose_variant(evaluations):
    """Predeclared conservative selection on human validation only."""
    chosen = "baseline"
    for variant in VARIANTS[1:]:
        current = evaluations[chosen]["humanLabelsOnly"]
        candidate = evaluations[variant]["humanLabelsOnly"]
        if candidate["correctAnswered"] > current["correctAnswered"] and candidate["wrongAnswered"] <= current["wrongAnswered"]:
            chosen = variant
    return chosen


def output_paths(run_id=None):
    import re
    if run_id is not None and not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", run_id):
        raise ValueError("Run ID must contain 1–40 lowercase letters, digits, hyphens or underscores")
    stem = "merchant_category_research" + ("_" + run_id if run_id else "")
    return ROOT / f"data/reports/{stem}.json", {variant: ROOT / f"data/models/{stem}_{variant}.json" for variant in VARIANTS}


def protect_existing_outputs(report_path, model_paths, inputs):
    for path in [report_path, *model_paths.values()]:
        if path.exists():
            saved = json.loads(path.read_text(encoding="utf-8"))
            previous = saved.get("inputSha256", saved.get("training", {}).get("inputSha256"))
            if previous != inputs:
                raise ValueError(f"Preserving historical output {path.name}: inputs changed; use a new --run-id")


def with_training_extension(rows, plan, allowed, additional_source=None):
    from training import prepare_merchant_training_extension as extension
    source = json.loads(extension.SOURCE.read_text(encoding="utf-8"))
    additions = extension.validate_extension(source["businesses"], rows, plan, allowed)
    saved = [json.loads(line) for line in extension.OUTPUT.read_text(encoding="utf-8").splitlines()]
    if additions != saved:
        raise ValueError("Rebuild validated training extension before fitting")
    paths = (extension.SOURCE, extension.OUTPUT)
    if additional_source is not None:
        extra = json.loads(additional_source.read_text(encoding="utf-8"))
        additions = extension.validate_extension(source["businesses"] + extra["businesses"], rows, plan, allowed)
        paths += (additional_source,)
    extended_plan = dict(plan, businessAssignments=dict(plan["businessAssignments"]))
    for row in additions:
        extended_plan["businessAssignments"][row["businessId"]] = "train"
    return rows + additions, extended_plan, paths


def main(run_id=None, include_extension=False, additional_source=None):
    if additional_source is not None and not include_extension:
        raise ValueError("Additional source requires --include-extension")
    if include_extension and not run_id:
        raise ValueError("Extension training requires a separate --run-id")
    report_path, model_paths = output_paths(run_id)
    rows = [json.loads(line) for line in BUSINESSES.read_text(encoding="utf-8").splitlines()]
    plan = json.loads(SPLIT.read_text(encoding="utf-8"))
    prepare(rows, plan)
    allowed = json.loads(TAXONOMY.read_text(encoding="utf-8"))["allowedCategories"]
    checked = audit(rows, plan, allowed, json.loads(FAMILIES.read_text(encoding="utf-8"))["families"])
    if checked["exactFormCrossFoldConflicts"] or checked["knownFamilyCrossFoldConflicts"]:
        raise ValueError("Resolve audited leakage before fitting")
    if any(checked["crossBusinessFormCollisions"].values()):
        raise ValueError("Ambiguous cross-business feature inputs need review")
    extension_paths = ()
    if include_extension:
        rows, plan, extension_paths = with_training_extension(rows, plan, allowed, additional_source)
    support = Counter(label(row)[0] for row in rows if plan["businessAssignments"][row["businessId"]] == "train" and label(row)[0] is not None)
    classes = [category for category in allowed if support[category] > 0]
    inputs = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in (BUSINESSES, SPLIT, TAXONOMY, FAMILIES, ROOT / "data/annotations/merchant_reviews.jsonl", *extension_paths)}
    protect_existing_outputs(report_path, model_paths, inputs)
    report = {"version": "1.0.0", "scope": "Merchant-name research only; assistant labels are weak supervision, not independent truth.",
              "inputSha256": inputs, "missingTrainingCategories": [category for category in allowed if not support[category]],
              "testInferencePerformed": False, "testMetrics": None,
              "selectionRule": "Fixed thresholds. Prefer baseline; switch only for strictly more correct answered HUMAN validation businesses with no increase in wrong answers. No tuning or selection against assistant labels/test.",
              "variants": {}, "syntheticTrainingViews": [],
              "limitations": ["Only five human validation businesses; selection is a small-sample pilot, not confidence calibration.",
                              "Synthetic forms inherit a base label; labelReviewerType identifies the base label reviewer, not approval of the generated spelling. They are not real bank descriptors or new identities/labels.",
                              "Raw softmax scores are uncalibrated; classes with fewer than three training businesses always abstain when top-ranked.",
                              "No SMS training, historical SMS reuse, runtime integration, or final test evaluation."]}
    # Validate every view for every treatment before writing any model outputs.
    all_groups = {variant: training_views(rows, plan, variant) for variant in VARIANTS}
    validations = {}
    for variant in VARIANTS:
        groups = all_groups[variant]
        model = fit(groups, classes, variant, inputs)
        # Evaluate the actual JSON-compatible flat export, including rounded weights.
        model = json.loads(json.dumps(model))
        path = model_paths[variant]
        path.write_text(json.dumps(model, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + "\n", encoding="utf-8")
        validation = evaluate(model, rows, plan, "validation")
        validations[variant] = validation
        training_diagnostics = evaluate(model, rows, plan, "train")
        training_diagnostics.pop("records")
        report["variants"][variant] = {"modelPath": str(path.relative_to(ROOT)), "modelSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                       "featureCount": len(model["features"]), "businessCount": len(groups),
                                       "viewCount": sum(map(len, groups)),
                                       "methodCounts": dict(Counter(view["method"] for group in groups for view in group)),
                                       "trainingDiagnosticsNotHoldout": training_diagnostics,
                                       "validation": validation}
        if variant == "augmented":
            report["syntheticTrainingViews"] = [view for group in groups for view in group if view["method"] not in ("canonical_name", "source_observed_alias")]
    report["selectedResearchVariant"] = choose_variant(validations)
    report["runtimePromotionAllowed"] = False
    report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    lines = ["# Merchant-category research comparison", "", "Merchant names only. No active engine change or final test inference. Softmax scores are uncalibrated.", "",
             "| Variant | Training businesses | Name forms | Human validation correct / answered / total | Combined research-label validation correct / answered / total |", "| --- | ---: | ---: | --- | --- |"]
    for variant in VARIANTS:
        item = report["variants"][variant]
        human, combined = validations[variant]["humanLabelsOnly"], validations[variant]["combinedResearchLabels"]
        lines.append(f"| {variant} | {item['businessCount']} | {item['viewCount']} | {human['correctAnswered']} / {human['answered']} / {human['businessCount']} | {combined['correctAnswered']} / {combined['answered']} / {combined['businessCount']} |")
    lines += ["", "Selected research variant: **" + report["selectedResearchVariant"] + "**. Ties retain the canonical-name baseline. Selection uses only human validation answers and fixed thresholds.", "",
              f"Assistant-label agreement is a research diagnostic, not independent accuracy. Five human validation businesses are insufficient to establish calibrated confidence or broad generalization. {len(report['missingTrainingCategories'])} target categories have no training businesses; low-support or weak-evidence predictions abstain. The active SMS engine is unchanged.", "",
              "Normalization preserves merchant prefixes such as LC Waikiki; it uses the shared digit helper but has its own versioned name-feature contract. Python and standalone TypeScript scoring share this contract. Models use flat feature-major weights and require no external ML runtime.", "",
              "Synthetic spelling/spacing forms are generated only in memory for fitting and documented once in the JSON report. They inherit existing labels, are capped at one per eligible training business, and keep each business's total weight equal. They are not new merchants or observed bank descriptors."]
    report_path.with_suffix('.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    fields = ("businessCount", "answered", "correctAnswered", "wrongAnswered", "abstained", "top1AccuracyBeforeAbstention")
    print(json.dumps({"selectedResearchVariant": report["selectedResearchVariant"],
                      "validation": {key: {kind: {field: value[scope][field] for field in fields} for kind, scope in (("human", "humanLabelsOnly"), ("combined", "combinedResearchLabels"))} for key, value in validations.items()},
                      "testInferencePerformed": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", help="Distinct output suffix; required when inputs change")
    parser.add_argument("--include-extension", action="store_true", help="Admit validated Jordan additions to training only")
    parser.add_argument("--additional-source", type=Path, help="Additional sourced training businesses; no holdout enrichment")
    args = parser.parse_args()
    main(args.run_id, args.include_extension, args.additional_source.resolve() if args.additional_source else None)
