import json
import time
import math
import sys
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from tests.python.test_suite_runner import run_python_suite
from tests.python.test_preprocessing_contract import main as run_python_preprocessing_contract
from tests.python.test_transaction_direction_contract import main as run_python_transaction_direction_contract
from tests.python.validate_test_corpus import validate_baseline
from tests.python.test_financial_numbers import main as run_python_financial_numbers

def main() -> int:
    corpus_errors = validate_baseline()
    if corpus_errors:
        print("FROZEN TEST CORPUS VALIDATION FAILED")
        for error in corpus_errors:
            print("- " + error)
        return 1

    if run_python_preprocessing_contract() != 0:
        return 1
    if run_python_transaction_direction_contract() != 0:
        return 1
    if run_python_financial_numbers() != 0:
        return 1
    category_suite = unittest.defaultTestLoader.loadTestsFromNames([
        "tests.python.test_merchant_category", "tests.python.test_merchant_training_extension",
        "tests.python.test_arabic_collection", "tests.python.test_transaction_behavior_contract",
        "tests.python.test_sms_provenance", "tests.python.test_sanitized_corpus"])
    if not unittest.TextTestRunner(verbosity=1).run(category_suite).wasSuccessful():
        return 1

    node_path = r"C:\Program Files\nodejs\node.exe"
    if not os.path.exists(node_path):
        print("TypeScript runner unavailable: Node.js was not found at the configured path.")
        return 1
    contract_process = subprocess.run(
        [node_path, str(ROOT / "tests" / "typescript" / "test_preprocessing_contract.ts")],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if contract_process.returncode != 0:
        print("TypeScript preprocessing contract failed")
        if contract_process.stdout.strip():
            print(contract_process.stdout.strip())
        if contract_process.stderr.strip():
            print(contract_process.stderr.strip())
        return 1
    print(contract_process.stdout.strip())
    score_contract_process = subprocess.run(
        [node_path, str(ROOT / "tests" / "typescript" / "test_transaction_direction_contract.ts")],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if score_contract_process.returncode != 0:
        print("TypeScript transaction-direction contract failed")
        if score_contract_process.stdout.strip():
            print(score_contract_process.stdout.strip())
        if score_contract_process.stderr.strip():
            print(score_contract_process.stderr.strip())
        return 1
    print(score_contract_process.stdout.strip())
    numeric_process = subprocess.run(
        [node_path, str(ROOT / "tests" / "typescript" / "test_financial_numbers.ts")],
        capture_output=True, text=True, encoding="utf-8",
    )
    if numeric_process.returncode != 0:
        print("TypeScript/browser financial-number contract failed")
        print(numeric_process.stdout.strip())
        print(numeric_process.stderr.strip())
        return 1
    print(numeric_process.stdout.strip())

    lab_process = subprocess.run(
        [node_path, str(ROOT / "tests/typescript/test_merchant_lab.ts")],
        capture_output=True, text=True, encoding="utf-8",
    )
    if lab_process.returncode != 0:
        print("Merchant tester integration failed")
        print(lab_process.stdout.strip())
        print(lab_process.stderr.strip())
        return 1
    print(lab_process.stdout.strip())

    suites = [
        ("Test Suite 1: QA Adversarial Edge Cases", ROOT / "tests" / "fixtures" / "qa_adversarial_cases.json"),
        ("Test Suite 2: Regression Bank Test Cases", ROOT / "tests" / "fixtures" / "test_suite_cases.json"),
    ]

    print("=" * 70)
    print("      MASROOF ENGINE CONSOLIDATED VERIFICATION TEST RUNNER       ")
    print("=" * 70)

    all_passed = True

    for title, filepath in suites:
        print(f"\n>>> Running Python Engine on: {title} ({filepath})")
        res_py = run_python_suite(filepath)
        print(f"  Total Cases: {res_py['total_cases']}")
        print(f"  Accuracy: {res_py['classification']['accuracy']}% (F1: {res_py['classification']['f1_score']}%)")
        print(f"  TP: {res_py['classification']['true_positives']} | TN: {res_py['classification']['true_negatives']}")
        print(f"  FP: {res_py['classification']['false_positives']} | FN: {res_py['classification']['false_negatives']}")
        print(f"  Latency (mean/p95/p99): {res_py['latency_ms']['mean']:.4f} ms / {res_py['latency_ms']['p95']:.4f} ms / {res_py['latency_ms']['p99']:.4f} ms")
        print("  Entity Accuracies:")
        for ent, stats in res_py['entity_extraction'].items():
            print(f"    - {ent:15s}: {stats['match']}/{stats['total']} ({stats['accuracy']}%)")
        print(f"  Mismatches: {len(res_py['mismatches'])}")

        if res_py['classification']['false_positives'] > 0 or res_py['classification']['false_negatives'] > 0 or len(res_py['mismatches']) > 0:
            all_passed = False

        # Run TypeScript Engine
        print(f"\n>>> Running TypeScript Engine on: {title} ({filepath})")
        cmd = [node_path, str(ROOT / "tests" / "typescript" / "test_suite_runner.ts"), str(filepath)]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        except OSError as error:
            all_passed = False
            print(f"  TypeScript runner could not start: {error}")
            continue
        lines = p.stdout.splitlines()
        for line in lines:
            if "Classification Accuracy:" in line or "FALSE POSITIVES:" in line or "FALSE NEGATIVES:" in line or "mean    :" in line or "p95     :" in line or "p99     :" in line or "Total Mismatches" in line:
                print("  " + line.strip())
        if p.returncode != 0:
            all_passed = False
            print(f"  TypeScript runner failed with exit code {p.returncode}")
            if p.stderr.strip():
                print("  " + p.stderr.strip())

    print("\n" + "=" * 70)
    if all_passed:
        print("ACTIVE BASELINE AND CONTRACT CHECKS PASSED")
        print("Prepared sanitized cases have a separate compatibility diagnostic before gate migration.")
    else:
        print("OVERALL STATUS: DEFECTS DETECTED")
    print("=" * 70)
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
