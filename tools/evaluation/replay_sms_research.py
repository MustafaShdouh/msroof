"""Check historical SMS research against its exact saved inputs, without fitting."""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from training.corpus_io import ROOT, recorded_source, sha256

EXPERIMENTS = {
    "sms_semantics_ab_v1": (None, "training.transactions.semantics_ab"),
    "sms_semantics_followup_v1": ("sms_semantics_ab_v1", "training.transactions.semantics_followup"),
    "sms_completion_context_v1": ("sms_semantics_followup_v1", "training.transactions.completion_context"),
}


@contextmanager
def frozen_workspace(run_id):
    """Use checked snapshots when live recording rules have legitimately evolved."""
    if run_id not in EXPERIMENTS:
        raise ValueError("Unknown frozen SMS experiment")
    hashes, current = {}, run_id
    while current:
        path = ROOT / f"data/reports/transactions/{current}.json"
        relative, expected = path.relative_to(ROOT).as_posix(), sha256(path)
        if relative in hashes and hashes[relative] != expected:
            raise ValueError("Parent report differs from recorded binding")
        report = json.loads(path.read_text(encoding="utf-8"))
        inputs = {**report["inputSha256"], **report["outputSha256"], relative: expected}
        attempt = ROOT / f"data/reports/transactions/{current}_attempt.json"
        inputs[attempt.relative_to(ROOT).as_posix()] = sha256(attempt)
        for relative, expected in inputs.items():
            if relative in hashes and hashes[relative] != expected:
                raise ValueError("Conflicting frozen source versions: " + relative)
            hashes[relative] = expected
        current = EXPERIMENTS[current][0]
    # Import-time and preparation dependencies have their own earlier snapshots.
    for tag in ("sms_semantics_preparation_v1", "sms_semantics_text_review_v2", "sms_semantics_propagation_v1", "sms_semantics_validation_review_v1"):
        manifest = ROOT / f"data/private/report_inputs/manifests/{tag}.json"
        dependencies = json.loads(manifest.read_text(encoding="utf-8"))
        report = ROOT / f"data/reports/{tag}.json"
        dependencies[report.relative_to(ROOT).as_posix()] = sha256(report)
        for relative, expected in dependencies.items():
            if relative in hashes and hashes[relative] != expected:
                raise ValueError("Conflicting historical dependency: " + relative)
            hashes[relative] = expected
    # The split loader also reads this corpus identity report and verifies its
    # artifact hashes against the already bound dataset/split bytes.
    identity = ROOT / "data/reports/sanitized_corpus_v1.json"
    hashes[identity.relative_to(ROOT).as_posix()] = sha256(identity)
    with tempfile.TemporaryDirectory(prefix="masroof-frozen-research-") as directory:
        destination = Path(directory)
        for relative, expected in hashes.items():
            target = (destination / relative).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("Invalid frozen source path")
            raw = recorded_source(relative, expected)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        for relative in hashes:
            for parent in Path(relative).parents:
                if parent == Path("."):
                    break
                marker, target = ROOT / parent / "__init__.py", destination / parent / "__init__.py"
                if marker.is_file() and not target.exists():
                    target.write_bytes(b"")
        yield destination


def replay(run_id):
    with frozen_workspace(run_id) as directory:
        result = subprocess.run([sys.executable, "-X", "utf8", "-m", EXPERIMENTS[run_id][1], "--check"],
                                cwd=directory, capture_output=True, text=True, encoding="utf-8", timeout=180)
        if result.returncode:
            raise ValueError(result.stderr or result.stdout)
    return {"runId": run_id, "frozenCheckPassed": True, "fitInvoked": False,
            "scope": "Historical inputs, not current recording rules; no artifact overwrite"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", choices=EXPERIMENTS)
    args = parser.parse_args()
    print(json.dumps(replay(args.run_id)))


if __name__ == "__main__":
    main()
