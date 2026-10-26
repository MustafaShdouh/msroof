"""Discover all engine safeguards and run the frozen compatibility gate."""
from pathlib import Path
import subprocess
import sys
import unittest

from tools.node_runtime import node_executable
from tests.python.test_suite_runner import run_python_suite
from tests.python.test_preprocessing_contract import main as check_preprocessing
from tests.python.test_transaction_direction_contract import main as check_transaction_contract
from tests.python.test_financial_numbers import main as check_financial_numbers
from tests.python.validate_test_corpus import validate_baseline, FIXTURE_ROOT

ROOT = Path(__file__).resolve().parent


def run_node(node, script, *arguments):
    result = subprocess.run([node, str(script), *(str(value) for value in arguments)],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return False
    print(f"TypeScript: {script.name} passed")
    return True


def main():
    errors = validate_baseline()
    if errors:
        print("Frozen corpus validation failed:\n" + "\n".join(errors))
        return 1
    for check in (check_preprocessing, check_transaction_contract, check_financial_numbers):
        if check() != 0:
            return 1

    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests/python"),
                                                pattern="test_*.py", top_level_dir=str(ROOT))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        return 1

    try:
        node = node_executable()
    except FileNotFoundError as error:
        print(error)
        return 1
    scripts = sorted(path for path in (ROOT / "tests/typescript").glob("test_*.ts")
                     if path.name != "test_suite_runner.ts")
    for script in scripts:
        if not run_node(node, script):
            return 1

    total = 0
    for name in ("qa_adversarial_cases.json", "test_suite_cases.json"):
        fixture = FIXTURE_ROOT / name
        outcome = run_python_suite(fixture)
        classification = outcome["classification"]
        if classification["false_positives"] or classification["false_negatives"] or outcome["mismatches"]:
            print(f"Python frozen gate failed: {name}")
            print(outcome["mismatches"])
            return 1
        if not run_node(node, ROOT / "tests/typescript/test_suite_runner.ts", fixture):
            return 1
        total += outcome["total_cases"]
        print(f"Frozen Python/TypeScript gate: {name}, {outcome['total_cases']} cases passed")

    print(f"Passed: {result.testsRun} Python tests, {len(scripts)} TypeScript suites, {total} frozen cases.")
    print("Development compatibility evidence; not independent accuracy or Hermes performance.")
    return 0


if __name__ == "__main__":
    if (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
