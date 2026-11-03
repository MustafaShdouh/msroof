"""Contract/parity, excluded probe groups and a one-fit budget; never train in tests."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.python.research.sms_completion_context import features, SmsCompletionContextModel
from training.transactions import completion_context as trial


def sample_model():
    return {"contractVersion": "1.0.0", "kind": "completion_context", "heads": {
        "completion": {"vocabulary": ["b|not debited", "w|debited"], "weights": [-2.0, 1.0], "intercept": 0.0,
                       "labels": {"negative": "non_transaction", "positive": "completed"}},
        "direction": {"vocabulary": ["w|credited"], "weights": [1.0], "intercept": 0.0,
                      "labels": {"negative": "outgoing", "positive": "incoming"}}}}


class SmsCompletionContextTests(unittest.TestCase):
    def test_order_and_negation_are_distinct_and_binary(self):
        self.assertIn("b|not debited", features("not debited"))
        self.assertNotIn("b|not debited", features("debited not"))
        self.assertIn("t|لم يتم الخصم", features("لَمْ يتم الخصم"))
        self.assertIn("w|num", features("١٢٫٥ JOD"))
        self.assertEqual(features("debited debited").count("w|debited"), 1)
        scorer = SmsCompletionContextModel(sample_model())
        self.assertEqual(scorer.predict("debited")["heads"]["completion"]["prediction"], "completed")
        self.assertEqual(scorer.predict("not debited")["heads"]["completion"]["prediction"], "non_transaction")
        self.assertEqual(scorer.predict("")["heads"]["completion"]["prediction"], "non_transaction")

    def test_invalid_exports_fail_before_inference(self):
        for problem in ("sort", "weight", "directionEncoding", "labels", "kind"):
            model = sample_model()
            if problem == "sort":
                model["heads"]["completion"]["vocabulary"].reverse()
            elif problem == "weight":
                model["heads"]["completion"]["weights"][0] = float("inf")
            elif problem == "directionEncoding":
                model["heads"]["direction"]["vocabulary"] = ["b|was credited"]
            elif problem == "labels":
                model["heads"]["completion"]["labels"]["positive"] = "uncertain"
            else:
                model["kind"] = "word"
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                SmsCompletionContextModel(model)

    def test_actual_typescript_and_browser_agree_on_unicode_and_negative_scope(self):
        texts = ["not debited", "debited not", "debited debited", "JO\\nتَمَّ خصم ١٢٫٥ JOD", "credited ۱۲٬۳۴۵.۶",
                 "constructor __proto__", "é e\u0301 𐐀² 😀", "x\u2028y\u0085z", "not 'debited'", ""]
        model = sample_model()
        actual = json.loads(trial.node([], {"model": model, "texts": texts, "browserRuntime": trial.node(["--bundle"])}))
        expected = [SmsCompletionContextModel(model).predict(text) for text in texts]
        self.assertEqual(actual["typescript"], expected)
        self.assertEqual(actual["browser"], expected)

    def test_bilingual_contrasts_never_split_training_and_probe(self):
        document = json.loads(trial.BATCH.read_text(encoding="utf-8"))
        rows = trial.expand_batch(document)
        groups = {row["authoringGroupId"] for row in rows}
        self.assertEqual(len(groups), 18)
        for group in groups:
            members = [row for row in rows if row["authoringGroupId"] == group]
            self.assertEqual(len(members), 4)
            self.assertEqual(len({row["fold"] for row in members}), 1)
            self.assertEqual(sum(row["weight"] for row in members), 1)
            self.assertEqual({(row["language"], row["target"]) for row in members},
                             {(lang, target) for lang in ("ar", "en") for target in ("completed", "non_transaction")})
            self.assertTrue(all(row["trainingEligible"] is False and row["independentEvaluationEligible"] is False for row in members))
        bad = deepcopy(document)
        bad["groups"][-1]["fold"] = "research_training"
        with self.assertRaises(ValueError):
            trial.expand_batch(bad)

    def test_vocabulary_never_sees_probe_only_words(self):
        words = trial.vocabulary(["payment was posted", "payment was posted yesterday"])
        self.assertNotIn("w|yesterday", words)
        self.assertNotIn("w|probeonly", words)
        self.assertIn("t|payment was posted", words)

    def test_existing_attempt_blocks_every_refit_before_preparation(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "attempt.json"
            ledger.write_text("{}", encoding="utf-8")
            with patch.object(trial, "ATTEMPT", ledger), patch.object(trial, "prepare", side_effect=AssertionError("already frozen")), \
                 patch.object(trial, "fit", side_effect=AssertionError("second fit")):
                with self.assertRaisesRegex(ValueError, "already attempted"):
                    trial.run(False)


if __name__ == "__main__":
    unittest.main()
