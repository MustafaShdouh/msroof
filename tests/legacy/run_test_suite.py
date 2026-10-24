import json
import os
from pathlib import Path
import sys

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.python.verify_engine import MasroofEngine

def main():
    suite_path = ROOT / "tests" / "fixtures" / "test_suite_cases.json"
    with open(suite_path, "r", encoding="utf-8") as f:
        suite = json.load(f)

    engine = MasroofEngine()
    cases = suite["testCases"]

    passed_binary = 0
    passed_full = 0
    failures_binary = []
    failures_extraction = []

    print(f"============================================================")
    print(f"RUNNING MASROOF TEST SUITE ({len(cases)} Cases)")
    print(f"============================================================")

    for c in cases:
        cid = c["id"]
        cat = c["category"]
        sender = c["sender"]
        body = c["body"]
        exp = c["expected"]

        res = engine.predict(sender, body)
        actual_valid = res["isValidTransaction"]
        exp_valid = exp["isValidTransaction"]

        if actual_valid != exp_valid:
            failures_binary.append((cid, cat, f"Binary classification mismatch: expected {exp_valid}, got {actual_valid} (Conf: {res['confidence']:.2f})", body))
            continue

        passed_binary += 1

        # If it's expected to be valid, verify entity extraction
        if exp_valid:
            d = res["data"]
            mismatches = []
            if exp["type"] and d["type"] != exp["type"]:
                mismatches.append(f"Type: exp {exp['type']} != got {d['type']}")
            if exp["amount"] is not None and d["amount"] != exp["amount"]:
                mismatches.append(f"Amount: exp {exp['amount']} != got {d['amount']}")
            if exp["currency"] and d["currency"] != exp["currency"]:
                mismatches.append(f"Currency: exp {exp['currency']} != got {d['currency']}")

            if mismatches:
                failures_extraction.append((cid, cat, ", ".join(mismatches), body, d))
                continue

        passed_full += 1

    print(f"\n--- TEST EXECUTION SUMMARY ---")
    print(f"Total Cases: {len(cases)}")
    print(f"Binary Classification Accuracy: {passed_binary}/{len(cases)} ({passed_binary/len(cases)*100:.2f}%)")
    print(f"Full Strict Pass (Binary + Exact Amount + Exact Currency + Exact Type): {passed_full}/{len(cases)} ({passed_full/len(cases)*100:.2f}%)")

    if failures_binary:
        print(f"\n[Binary Failures ({len(failures_binary)})]:")
        for cid, cat, msg, body in failures_binary:
            print(f" - [{cid}] ({cat}): {msg}")
            print(f"   Body: {repr(body[:80])}")

    if failures_extraction:
        print(f"\n[Extraction Mismatches ({len(failures_extraction)})]:")
        for cid, cat, msg, body, actual_data in failures_extraction:
            print(f" - [{cid}] ({cat}): {msg}")
            print(f"   Body: {repr(body[:80])}")
            print(f"   Extracted: {actual_data}")

if __name__ == "__main__":
    main()
