"""Retire checked working copies; preserve private snapshots and all Git history."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from training.corpus_io import historical_path, sha256, write_immutable, ARCHIVES

LAYOUT = ROOT / "config/contracts/corpus_layout.json"
REPORT = ROOT / "data/reports/legacy_corpus_retirement_v1.json"
RELOCATED_REPLACEMENTS = {
    "training/prepare_sanitized_corpus.py": "training/corpus/prepare.py",
    "training/evaluate_arabic_support.py": "training/evaluation/arabic.py",
}


def checked_targets(root=ROOT):
    plan = json.loads((root / "config/contracts/corpus_layout.json").read_text(encoding="utf-8"))
    targets = []
    for item in plan["retired"]:
        target = (root / item["path"]).resolve()
        if not target.is_relative_to(root.resolve()):
            raise ValueError("Retirement path escapes repository")
        archived = historical_path(item["path"], root)
        if sha256(archived) != item["historicalSha256"]:
            raise ValueError("Retirement plan differs from historical snapshot")
        replacement = (root / RELOCATED_REPLACEMENTS.get(item["replacement"], item["replacement"])).resolve()
        if not replacement.is_relative_to(root.resolve()) or not replacement.is_file():
            raise ValueError("Missing replacement: " + item["replacement"])
        if target.exists() and sha256(target) != item["historicalSha256"]:
            raise ValueError("Working copy changed; refusing retirement: " + item["path"])
        targets.append(target)
    return plan, targets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.apply and args.check:
        parser.error("Choose --apply or --check")
    plan, targets = checked_targets()
    if args.apply:
        # Every target and replacement is checked before the first removal.
        # Each file remains recoverable through its hash-checked private copy.
        for path in targets:
            if path.exists():
                path.unlink()
    if args.check or args.apply:
        if any(path.exists() for path in targets):
            raise ValueError("Retired working copies still exist")
        active_model = ROOT / "data/models/masroof_model.json"
        if sha256(active_model) != sha256(historical_path("data/models/masroof_model.json")):
            raise ValueError("Active model differs from the preserved baseline")
        report = {
            "version": "1.0.0", "scope": plan["scope"],
            "layoutSha256": sha256(LAYOUT),
            "privateArchiveManifestSha256": {directory: sha256(ROOT / directory / "manifest.json") for directory in ARCHIVES},
            "retiredWorkingPaths": [item["path"] for item in plan["retired"]],
            "activeDatasetSha256": sha256(ROOT / plan["active"]["dataset"]),
            "activeSplitSha256": sha256(ROOT / plan["active"]["split"]),
            "activeBioSha256": sha256(ROOT / plan["active"]["bio"]),
            "activeModelSha256": sha256(active_model),
            "remoteHistoryChanged": False, "modelFittedOrPromoted": False,
            "remainingLimit": "Old commits and legacy model vocabulary remain; no complete anonymization or independent-accuracy claim",
        }
        content = json.dumps(report, indent=2) + "\n"
        if args.check:
            if not REPORT.exists() or REPORT.read_text(encoding="utf-8") != content:
                raise ValueError("Retirement report missing or stale")
        else:
            write_immutable(REPORT, content)
    print(f"Legacy working copies: {len(targets)} {'retired and verified' if args.check or args.apply else 'checked for retirement (dry run)'}; snapshots retained privately; Git history unchanged")


if __name__ == "__main__":
    main()
