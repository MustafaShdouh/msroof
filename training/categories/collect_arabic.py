"""Prepare new Arabic metadata without fitting models or evaluating holdouts."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from training.categories import extend_training as extension

SOURCE = ROOT / "data/sources/businesses/jordan_arabic_collection.json"
ROUND3 = ROOT / "data/sources/businesses/jordan_training_round3.json"
OUTPUT = ROOT / "data/annotations/merchant_arabic_collection.jsonl"
REPORT = ROOT / "data/reports/merchant_arabic_collection_audit.json"


def prepare_collection(base, plan, allowed, prior, incoming):
    earlier = extension.validate_extension(prior, base, plan, allowed)
    combined = extension.validate_extension(prior + incoming, base, plan, allowed)
    earlier_ids = {row["businessId"] for row in earlier}
    additions = [row for row in combined if row["businessId"] not in earlier_ids]
    if len(additions) != len(incoming):
        raise ValueError("Collection must add distinct identities")
    return additions


def main():
    base = [json.loads(line) for line in extension.BASE.read_text(encoding="utf-8").splitlines()]
    plan = json.loads(extension.SPLIT.read_text(encoding="utf-8"))
    allowed = json.loads(extension.TAXONOMY.read_text(encoding="utf-8"))["allowedCategories"]
    prior = json.loads(extension.SOURCE.read_text(encoding="utf-8"))["businesses"] + json.loads(ROUND3.read_text(encoding="utf-8"))["businesses"]
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    additions = prepare_collection(base, plan, allowed, prior, source["businesses"])
    OUTPUT.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in additions), encoding="utf-8")
    paths = (SOURCE, ROUND3, extension.SOURCE, extension.BASE, extension.SPLIT, extension.TAXONOMY)
    report = {
        "version": "1.0.0", "scope": "Prospective Arabic training-only metadata; not fitted, not real SMS or independent human truth.",
        "newBusinesses": len(additions), "newCategoryCounts": dict(sorted(Counter(row["assistantReviewedCategory"] for row in additions).items())),
        "arabicCanonicalNames": sum(any('\u0621' <= c <= '\u064a' for c in row["name"]) for row in additions),
        "deferredCandidates": source.get("deferredCandidates", []),
        "inputSha256": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        "outputSha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "leakageAuditScope": "Exact aliases/features and conservative prefixes against original200; duplicate aliases/features against all25 existing additions. Corporate ownership audit is bounded, not exhaustive.",
        "modelsTrained": False, "finalTestInferencePerformed": False,
        "rawSmsProvenance": "See data/sources/transactions/jordan_context_evidence.json; seed originals versus Gemini descendants not identified record by record. No independent SMS admitted.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("newBusinesses", "newCategoryCounts", "arabicCanonicalNames", "modelsTrained", "finalTestInferencePerformed")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
