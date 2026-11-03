"""Run the unchanged proposal assertion against its preserved pre-execution state."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from training.corpus_io import ROOT, recorded_source


def run_proposal_test():
    manifest=ROOT/"data/private/report_inputs/manifests/core_money_r1_aux_proposal.json"
    hashes=json.loads(manifest.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="masroof-proposal-test-") as directory:
        root=Path(directory).resolve()
        for relative,expected in hashes.items():
            target=(root/relative).resolve()
            if not target.is_relative_to(root):raise ValueError("Snapshot path escapes test context")
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(recorded_source(relative,expected))
        return subprocess.run([sys.executable,"-X","utf8","-m","unittest",
            "tests.python.test_auxiliary_status_protocol.AuxiliaryStatusProtocolTests.test_frozen_view_baseline_metadata_and_unapproved_budget"],
            cwd=root,capture_output=True,text=True,encoding="utf-8",timeout=60)
