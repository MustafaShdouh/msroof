"""Verify Python preprocessing against the versioned contract vectors."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.python.preprocessing import PREPROCESSING_CONTRACT_VERSION, preprocess_message, tokenize_features


def main() -> int:
    fixture_root = ROOT / "tests" / "fixtures"
    contract = json.loads((fixture_root / "preprocessing_contract.json").read_text(encoding="utf-8"))
    cases = json.loads((fixture_root / "preprocessing_contract_cases.json").read_text(encoding="utf-8"))
    if contract.get("version") != PREPROCESSING_CONTRACT_VERSION:
        print("Preprocessing contract version mismatch")
        return 1
    failures = []
    for case in cases:
        normalized = preprocess_message(case["raw"])
        features = tokenize_features(normalized)
        if normalized != case["normalized"] or features != case["features"]:
            failures.append(case["id"])
    if failures:
        print("Python preprocessing contract failures:", ", ".join(failures))
        return 1
    print(f"Python preprocessing contract passed: {len(cases)} vectors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
