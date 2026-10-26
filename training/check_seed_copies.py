"""Bounded check for known full seed text in working files; not anonymization."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training.audit_sms_provenance import blocks, canonical, digest
from training.corpus_io import write_immutable

REPORT = ROOT / "data/reports/known_seed_copy_scan_v1.json"


def string_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from string_values(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from string_values(item)


def contains_seed(content, seeds):
    # Handle ordinary source literals and decoded nested JSON string values.
    views = [content, content.replace("\\r", "\r").replace("\\n", "\n")]
    try:
        views.extend(string_values(json.loads(content)))
    except ValueError:
        pass
    normalized = canonical("\n".join(views))
    return any(seed in normalized for seed in seeds)


def scan(root=ROOT):
    manifest = json.loads((root / "data/sources/transactions/seed_audit_manifest.json").read_text(encoding="utf-8"))
    seeds = []
    for source in manifest["sources"]:
        raw = (root / source["path"]).read_bytes()
        if digest(raw) != source["sha256"]:
            raise ValueError("Original seed source changed")
        seeds.extend(canonical(row["text"]) for row in blocks(raw.decode("utf-8-sig")))
    process = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                             cwd=root, check=True, capture_output=True)
    matches = []
    for relative in sorted(set(process.stdout.decode("utf-8").split("\0")) - {""}):
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            continue
        # Private sources are ignored; a newly tracked private path is an error.
        if (relative.startswith(("data/private/", "DATA_YOU_WANT/", ".local-backups/"))
                or (relative.startswith("data/raw/") and path.suffix == ".txt")):
            raise ValueError("Private source path is unexpectedly tracked: " + relative)
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            continue
        if contains_seed(text, seeds):
            matches.append(relative)
    return {"scanVersion": "1.0.0", "scope": "Known complete seed text after whitespace/Unicode/digit normalization in tracked and nonignored working files",
            "knownSeedBlocks": len(seeds), "matchedWorkingPaths": matches,
            "gitHistoryScanned": False, "modelVocabularyReviewed": False,
            "completePrivacyRemediation": False,
            "limits": "No proof against partial identifiers, paraphrases or unknown private data; old Git objects and learned legacy vocabulary remain"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = scan()
    if report["matchedWorkingPaths"]:
        raise ValueError("Known full seed copies remain in: " + ", ".join(report["matchedWorkingPaths"]))
    content = json.dumps(report, indent=2) + "\n"
    if args.check:
        if not REPORT.exists() or REPORT.read_text(encoding="utf-8") != content:
            raise ValueError("Known-seed copy scan missing or stale")
    else:
        write_immutable(REPORT, content)
    print(f"Known full-seed copy scan: {report['knownSeedBlocks']} blocks, zero matching working paths; historical Git objects and partial identifiers outside scope")


if __name__ == "__main__":
    main()
