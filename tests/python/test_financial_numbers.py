"""Assert equivalent numeric scripts preserve Jordan SMS behavior and guards."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.python.preprocessing import normalize_financial_numbers
from src.python.verify_engine import MasroofEngine


def main() -> int:
    vectors = json.loads((ROOT / "tests/fixtures/financial_number_cases.json").read_text(encoding="utf-8"))
    for case in vectors:
        if normalize_financial_numbers(case["raw"]) != case["normalized"]:
            raise AssertionError(f"Number normalization failed: {case['id']}")
        if "value" in case and abs(MasroofEngine.parse_number(case["raw"]) - case["value"]) > 1e-12:
            raise AssertionError(f"Number parsing failed: {case['id']}")
    engine = MasroofEngine()
    if engine.predict(None, None, is_contact=True)["isValidTransaction"]:
        raise AssertionError("Contact guard must run before message normalization")
    equivalent_cases = 0
    for name in ("test_suite_cases.json", "qa_adversarial_cases.json"):
        payload = json.loads((ROOT / "tests/fixtures" / name).read_text(encoding="utf-8"))
        cases = payload["testCases"] if isinstance(payload, dict) else payload
        for case in cases:
            baseline = engine.predict(case["sender"], case["body"])
            for digits, separators in (("٠١٢٣٤٥٦٧٨٩", False), ("۰۱۲۳۴۵۶۷۸۹", False), ("٠١٢٣٤٥٦٧٨٩", True)):
                body = case["body"].translate(str.maketrans("0123456789", digits))
                if separators:
                    body = body.replace(".", "٫").replace(",", "٬")
                if engine.predict(case["sender"], body) != baseline:
                    raise AssertionError(f"Numeric script changed a structured result: {case['id']}")
                equivalent_cases += 1
    for sender in ("+٩٦٢٧٩١٢٣٤٥٦٧", "٠٧٩١٢٣٤٥٦٧", "+۹۶۲۷۹۱۲۳۴۵۶۷"):
        result = engine.predict(sender, "تم شراء بقيمة ١٢٫٥٠ دينار لدى مطعم")
        if result["isValidTransaction"] or result["reason"] != "Personal sender (phone number)":
            raise AssertionError("Unicode phone number bypassed personal-sender guard")
    print(f"Python financial numbers passed: {len(vectors)} vectors, {equivalent_cases} full-result equivalence cases, 3 sender guards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
