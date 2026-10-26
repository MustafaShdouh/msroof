"""Contract conformance, contextual counterexamples and complete runtime parity."""
import json
from pathlib import Path
import re
import subprocess
import unittest
from unittest.mock import patch

from src.python.engine import MasroofEngine
from tools.contracts.validate_transaction_behavior import validate_result
from tools.node_runtime import node_executable

ROOT = Path(__file__).resolve().parents[2]
NODE = node_executable()


def load(name):
    return json.loads((ROOT / "tests/fixtures" / name).read_text(encoding="utf-8"))


def probe(cases, ui_case=None):
    p = subprocess.run([NODE, str(ROOT / "tools/evaluation/probe_detailed.ts")],
                       input=json.dumps({"cases": cases, "uiCase": ui_case}), capture_output=True,
                       text=True, encoding="utf-8", cwd=ROOT)
    if p.returncode:
        raise AssertionError(p.stderr)
    return json.loads(p.stdout)


class DetailedAssessmentTests(unittest.TestCase):
    def test_policy_outputs_and_frozen_annotation_disagreement(self):
        cases = load("transaction_behavior_cases.json")["cases"]
        outputs = probe(cases)["rows"]
        engine, disagreements = MasroofEngine(), []
        for case, other in zip(cases, outputs):
            with self.subTest(case=case["id"]):
                result = engine.predict_detailed(case["input"])
                validate_result(result)
                self.assertEqual(result, other["typescript"])
                self.assertEqual(result, other["browser"])
                self.assertEqual(result["trackingDecision"], case["expected"]["trackingDecision"])
                for field, value in case["expected"].items():
                    actual = result[field]
                    if (set(actual) != set(value) if field == "reasonCodes" else actual != value):
                        disagreements.append((case["id"], field))
        # The frozen case contains no currency token, but labels it explicit.
        # Report this known annotation conflict without changing its bytes.
        self.assertEqual(disagreements, [("completed_missing_amount", "currencyResolution")])

    def test_contextual_controls_and_browser_review_display(self):
        cases = load("detailed_assessment_cases.json")["cases"]
        ui_case = next(case for case in cases if case["id"] == "atm_activity")
        outputs = probe(cases, ui_case["input"])
        self.assertEqual(outputs["ui"]["title"], "Review required")
        self.assertEqual(outputs["ui"]["assessment"]["trackingDecision"], "review")
        engine = MasroofEngine()
        for case, other in zip(cases, outputs["rows"]):
            with self.subTest(case=case["id"]):
                result = engine.predict_detailed(case["input"])
                validate_result(result)
                self.assertEqual(result, other["typescript"])
                self.assertEqual(result, other["browser"])
                for key, expected in case["expect"].items():
                    self.assertEqual(result[key], expected, key)

    def test_authorization_contrasts_still_hold_in_detailed_api(self):
        controls = load("authorization_request_cases.json")["cases"]
        cases = [{"id": row["id"], "input": {"text": row["body"]}} for row in controls]
        outputs, engine = probe(cases)["rows"], MasroofEngine()
        for row, case, other in zip(controls, cases, outputs):
            with self.subTest(case=row["id"]):
                result = engine.predict_detailed(case["input"])
                validate_result(result)
                self.assertEqual(result, other["typescript"])
                self.assertEqual(result, other["browser"])
                if row["request"]:
                    self.assertEqual(result["transactionStatus"], "non_transaction")
                    self.assertEqual(result["trackingDecision"], "exclude")
                    self.assertIsNone(result["amount"])
                elif row.get("accepted"):
                    self.assertEqual(result["trackingDecision"], "include")

    def test_metadata_and_digit_scripts_preserve_decisions(self):
        base = {"text": "JOD 18.750 debited from account *6284 at LOCAL SHOP. Available balance JOD 170.125."}
        expected = MasroofEngine().predict_detailed(base)
        cases = []
        for index, (digits, sender, contact) in enumerate((("0123456789", "", False), ("٠١٢٣٤٥٦٧٨٩", "+٩٦٢٧٠٠٠٠٠٠٠٠", True), ("۰۱۲۳۴۵۶۷۸۹", "Saved contact", True))):
            text = base["text"].translate(str.maketrans("0123456789", digits))
            cases.append({"id": str(index), "input": {"text": text, "sender": sender, "isContact": contact}})
        for case, other in zip(cases, probe(cases)["rows"]):
            actual = MasroofEngine().predict_detailed(case["input"])
            self.assertEqual(actual, expected)
            self.assertEqual(actual, other["typescript"])
            self.assertEqual(actual, other["browser"])

    def test_parsing_repairs_preserve_raw_names_and_numeric_scripts(self):
        controls = [case for case in load("detailed_assessment_cases.json")["cases"]
                    if case["id"].startswith(("parsing_", "purchase_", "direction_"))]
        cases = []
        for case in controls:
            for script, digits in enumerate(("0123456789", "٠١٢٣٤٥٦٧٨٩", "۰۱۲۳۴۵۶۷۸۹")):
                def variant(text):
                    if script:
                        text = re.sub(r"(?<=[0-9])[.,](?=[0-9])", lambda match: "٫" if match[0] == "." else "٬", text)
                    return text.translate(str.maketrans("0123456789", digits))
                cases.append({"id": case["id"] + ":" + str(script),
                              "input": {"text": variant(case["input"]["text"])},
                              "expect": {key: variant(value) if isinstance(value, str) else value
                                         for key, value in case["expect"].items()}})
        engine = MasroofEngine()
        for case, other in zip(cases, probe(cases)["rows"]):
            with self.subTest(case=case["id"]):
                result = engine.predict_detailed(case["input"])
                validate_result(result)
                self.assertEqual(result, other["typescript"])
                self.assertEqual(result, other["browser"])
                for key, expected in case["expect"].items():
                    self.assertEqual(result[key], expected, key)

    def test_malformed_input_and_clear_otp_do_not_need_model_scoring(self):
        engine = MasroofEngine()
        with patch.object(engine, "_score_tokens", side_effect=AssertionError("Unexpected scoring")):
            for value in (None, {}, {"text": None}, {"text": 42}, {"text": ""}, {"text": "Your code to complete your payment of JOD 20 is 684291."}):
                result = engine.predict_detailed(value)
                validate_result(result)
                self.assertEqual(result["trackingDecision"], "exclude")
