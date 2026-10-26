from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.python.preprocessing import PREPROCESSING_CONTRACT_VERSION, preprocess_message, tokenize_features
from src.python.research.transaction_direction import CONTRACT_VERSION, evaluate_model


def main() -> int:
    fixture_root = ROOT / "tests" / "fixtures"
    contract = json.loads((fixture_root / "transaction_direction_contract.json").read_text(encoding="utf-8"))
    vectors = json.loads((fixture_root / "transaction_direction_score_cases.json").read_text(encoding="utf-8"))
    if contract.get("contractVersion") != CONTRACT_VERSION or contract.get("preprocessingVersion") != PREPROCESSING_CONTRACT_VERSION:
        print("Transaction-direction contract version mismatch")
        return 1
    failures = []
    for case in vectors["cases"]:
        result = evaluate_model(vectors["model"], tokenize_features(preprocess_message(case["raw"])))
        for field in ("transactionLogit", "transactionProbability", "directionLogit", "incomeProbability"):
            if not math.isclose(result[field], case[field], rel_tol=0.0, abs_tol=1e-12):
                failures.append(f"{case['id']}:{field}")
        for field in ("isTransaction", "type"):
            if result[field] != case[field]:
                failures.append(f"{case['id']}:{field}")
    if failures:
        print("Python transaction-direction contract failures:", ", ".join(failures))
        return 1
    print(f"Python transaction-direction contract passed: {len(vectors['cases'])} vectors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
