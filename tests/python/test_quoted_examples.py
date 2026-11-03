"""Explicit example introductions are not receipt evidence; quotes alone are allowed."""
import json
import unittest
from unittest.mock import patch

from src.python.engine import MasroofEngine
from tests.python.test_detailed_assessment import probe
from tools.contracts.validate_transaction_behavior import validate_result
from tools.evaluation.replay_sms_research import frozen_workspace
from training.corpus_io import ROOT
from training.evaluation.behavior import canonical_result


class QuotedExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((ROOT / "tests/fixtures/quoted_example_cases.json").read_text(encoding="utf-8"))["cases"]

    def test_bilingual_controls_across_numeric_scripts_and_sender_metadata(self):
        engine, inputs, expected = MasroofEngine(), [], {}
        for case in self.cases:
            for script, digits in enumerate(("0123456789", "٠١٢٣٤٥٦٧٨٩", "۰۱۲۳۴۵۶۷۸۹")):
                for sender, contact in (("", False), ("Saved contact", True)):
                    key = f"{case['id']}:{script}:{contact}"
                    text = case["text"].translate(str.maketrans("0123456789", digits))
                    inputs.append({"id": key, "input": {"text": text, "sender": sender, "isContact": contact}})
                    expected[key] = case
        outputs = probe(inputs)["rows"]
        self.assertEqual(len(outputs), len(inputs))
        for row, other in zip(inputs, outputs, strict=True):
            with self.subTest(case=row["id"]):
                result = engine.predict_detailed(row["input"])
                validate_result(result)
                self.assertEqual(result, other["typescript"])
                self.assertEqual(result, other["browser"])
                case = expected[row["id"]]
                self.assertEqual(result["trackingDecision"], case["decision"])
                self.assertEqual(result["transactionStatus"], case["status"])
                if "amount" in case:
                    self.assertEqual(result["amount"], case["amount"])
                legacy = engine.predict(row["input"]["sender"], row["input"]["text"], row["input"]["isContact"])
                self.assertEqual(canonical_result(legacy), other["legacyTypescript"])
                self.assertEqual(other["legacyTypescript"], other["legacyBrowser"])

    def test_known_example_rejections_do_not_need_a_learned_score(self):
        engine = MasroofEngine()
        with patch.object(engine, "_score_tokens", side_effect=AssertionError("Example rejection must not use model score")):
            for case in self.cases:
                if case["decision"] != "exclude":
                    continue
                result = engine.predict_detailed({"text": case["text"]})
                self.assertEqual(result["reasonCodes"], ["personal_conversation"])
                for field in ("amount", "currency", "merchantOrCounterparty", "expenseCategory"):
                    self.assertIsNone(result[field])

    def test_built_page_shows_excluded_for_both_reported_examples(self):
        for case in self.cases[:2]:
            request = {"text": case["text"]}
            result = probe([{"id": case["id"], "input": request}], request)
            self.assertEqual(result["ui"]["assessment"]["trackingDecision"], "exclude")
            self.assertEqual(result["ui"]["title"], "Exclude")

    def test_historical_workspace_keeps_original_rule_and_seven_tests(self):
        with frozen_workspace("sms_semantics_followup_v1") as root:
            old = json.loads((root / "config/contracts/transaction_evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(old["version"], "1.0.5")
            source = (root / "tests/python/test_sms_semantics_followup.py").read_text(encoding="utf-8")
            self.assertIn("cls.selected, cls.sources", source)
        self.assertEqual(json.loads((ROOT / "config/contracts/transaction_evidence.json").read_text(encoding="utf-8"))["version"], "1.0.20")
