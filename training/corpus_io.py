"""Explicit current inputs, checked historical reads, and immutable tool outputs."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/training/sanitized_v1/transactions.json"
SPLIT = ROOT / "data/training/splits/transaction_direction_sanitized_v1.json"
FIXTURES = ROOT / "tests/fixtures/sanitized_v1"
BIO = ROOT / "data/training/sanitized_v1/bio_training_data.json"
ARCHIVES = ("data/private/historical_corpus_v1", "data/private/legacy_tools_v1")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def historical_path(relative, root=ROOT):
    """Resolve a registered immutable input; never silently use a working copy."""
    for directory in ARCHIVES:
        archive = root / directory
        manifest = archive / "manifest.json"
        if not manifest.exists():
            continue
        hashes = json.loads(manifest.read_text(encoding="utf-8"))["filesSha256"]
        if relative not in hashes:
            continue
        path = (archive / relative).resolve()
        if not path.is_relative_to(archive.resolve()) or sha256(path) != hashes[relative]:
            raise ValueError("Historical input missing or changed: " + relative)
        return path
    raise FileNotFoundError("Private historical snapshot required for " + relative + "; routine development uses sanitized_v1")


def recorded_source(relative, expected, root=ROOT):
    """Read exact historical source bytes after a producer is retired or moved."""
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("Invalid recorded source path or checksum")
    blob = root / "data/private/report_inputs/blobs" / expected
    for candidate in (target, blob):
        if candidate.is_file():
            raw = candidate.read_bytes()
            if hashlib.sha256(raw).hexdigest() == expected:
                return raw
            if candidate == blob:
                raise ValueError("Recorded source blob was modified")
    try:
        archived = historical_path(relative, root).read_bytes()
        if hashlib.sha256(archived).hexdigest() == expected:
            return archived
    except FileNotFoundError:
        pass
    # Public source producers are recoverable from the pushed cleanup checkpoint.
    # No network access, working-tree restoration or unchecked fallback bytes.
    result = subprocess.run(["git", "show", "checkpoint/pre-cleanup-2026-10-26:" + relative],
                            cwd=root, capture_output=True)
    if result.returncode == 0 and hashlib.sha256(result.stdout).hexdigest() == expected:
        return result.stdout
    raise FileNotFoundError("Checksum-matching source snapshot required for " + relative)


def write_immutable(path, content):
    """Identical reruns are allowed; changed inputs need a new artifact version."""
    path = Path(path)
    if path.exists() and path.read_text(encoding="utf-8") != content:
        raise ValueError("Refusing changed-input overwrite; select a new output/version: " + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8", newline="\n")


def snapshot_report_inputs(tag, hashes, root=ROOT):
    """Preserve report inputs privately, deduplicated by byte hash across runs."""
    if not re.fullmatch(r"[a-z0-9_]{1,80}", tag):
        raise ValueError("Invalid report snapshot tag")
    archive = root / "data/private/report_inputs"
    for relative, expected in hashes.items():
        source = (root / relative).resolve()
        if not source.is_relative_to(root.resolve()):
            raise ValueError("Report input escapes repository")
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("Report input changed before snapshot: " + relative)
        blob = archive / "blobs" / expected
        if blob.exists() and sha256(blob) != expected:
            raise ValueError("Private report snapshot blob changed")
        if not blob.exists():
            blob.parent.mkdir(parents=True, exist_ok=True)
            blob.write_bytes(raw)
    write_immutable(archive / "manifests" / (tag + ".json"), json.dumps(hashes, indent=2, sort_keys=True) + "\n")


def load_development_split(records, dataset=DATASET, split_path=SPLIT):
    frozen = json.loads((ROOT / "data/reports/sanitized_corpus_v1.json").read_text(encoding="utf-8"))["artifactSha256"]
    for path, active in ((dataset, DATASET), (split_path, SPLIT)):
        if path.resolve() == active.resolve() and sha256(path) != frozen[active.relative_to(ROOT).as_posix()]:
            raise ValueError("Active corpus/split differs from frozen preparation evidence")
    split = json.loads(split_path.read_text(encoding="utf-8"))
    if (split.get("corpusVersion") != "sanitized-corpus-1.0.0" or split.get("splitVersion") != "1.0.0"
            or split.get("datasetSha256") != sha256(dataset) or split.get("recordCount") != len(records)):
        raise ValueError("Split does not identify the sanitized corpus/version")
    train, validation = split["trainIndices"], split["validationIndices"]
    combined = train + validation
    if (not train or not validation or len(combined) != len(records)
            or any(type(i) is not int for i in combined) or set(combined) != set(range(len(records)))):
        raise ValueError("Split must cover all rows once across two nonempty folds")
    train_set, val_set = set(train), set(validation)
    groups = split.get("groups", [])
    grouped = [index for group in groups for index in group["indices"]]
    if (len(grouped) != len(records) or set(grouped) != set(range(len(records)))
            or any(not (set(group["indices"]) <= train_set or set(group["indices"]) <= val_set) for group in groups)):
        raise ValueError("Split groups are incomplete or cross folds")
    return train, validation, split
