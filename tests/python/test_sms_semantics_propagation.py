"""Literal/slot guard, task separation, duplicate weighting and non-admission checks."""
from collections import defaultdict
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from training.corpus.propagation import build, assess_guard, frame, deduplicate, validate_proposals, normalize_text
from training.corpus.semantics import prepare, DATASET
from training.corpus.review_semantics import build as review_build


class SmsSemanticsPropagationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.validation, cls.report, _ = build()
        cls.drafts, _, _, _, _ = prepare()
        cls.reviewed, _, _ = review_build()
        cls.sources = json.loads(DATASET.read_text(encoding="utf-8"))

    def test_training_only_coverage_and_no_automatic_admission(self):
        self.assertEqual(len(self.rows), 1702)
        self.assertEqual(len(self.validation), 22)
        self.assertEqual(self.report["directReviewedCandidates"], 66)
        self.assertGreater(self.report["proposedDescendantCandidates"], 0)
        for row in self.rows:
            self.assertEqual(row["fold"], "train")
            self.assertFalse(row["trainingEligible"])
            self.assertFalse(row["independentEvaluationEligible"])
            self.assertTrue(row["proposalOnly"])
            self.assertLessEqual(set(row["candidateTargets"]), {"transactionStatus", "direction"})
        self.assertFalse({row["recordId"] for row in self.rows} & {row["recordId"] for row in self.validation})
        for row in self.validation:
            self.assertEqual(row["fold"], "validation")
            self.assertEqual(row["annotations"], {})
            self.assertFalse(row["trainingEligible"])

    def test_group_blocks_and_uncertainty_retained(self):
        blocked = [row for row in self.rows if row["admissionBlockers"]]
        self.assertEqual(len(blocked), 410)
        self.assertTrue(all(row["outcome"] == "blocked" and not row["candidateTargets"] for row in blocked))
        uncertain = [row for row in self.rows if row["reason"] == "unsupported_uncertain_completion"]
        self.assertEqual(len(uncertain), 9)
        self.assertTrue(all(not row["candidateTargets"] for row in uncertain))

    def test_family_weight_is_not_repeated_example_count(self):
        weights = defaultdict(float)
        for row in self.rows:
            for field, target in row["candidateTargets"].items():
                weights[row["sourceExpressionId"], field] += target["proposedTrainingWeight"]
        for weight in weights.values():
            self.assertAlmostEqual(weight, 1.0, places=12)
        self.assertEqual(self.report["candidateSourceExpressions"], 66)
        self.assertGreater(self.report["outcomeCounts"].get("duplicate", 0), 0)

    def test_no_student_or_merchant_inference(self):
        with patch("src.python.engine.MasroofEngine.predict", side_effect=AssertionError("student forbidden")), \
             patch("src.python.engine.MasroofEngine.predict_detailed", side_effect=AssertionError("student forbidden")), \
             patch("src.python.research.merchant_category.predict", side_effect=AssertionError("reserved inference forbidden")):
            _, _, report, _ = build()
        self.assertFalse(report["modelFitted"])

    def test_changed_slot_cannot_hide_decline_or_ownership(self):
        parent = {"text": "JOD 5.000 credited from ALICE.", "expected_merchant": "ALICE"}
        reviewed = {"annotations": {"transactionStatus": {"value": "completed", "evidence": [{"text": "credited"}]},
                                    "direction": {"value": "incoming", "evidence": [{"text": "credited"}]},
                                    "amount": {"evidence": [{"text": "5.000"}]}}}
        valid = {"text": "JOD 7.000 credited from BOB.", "expected_merchant": "BOB"}
        reason, _, targets = assess_guard(parent, valid, reviewed)
        self.assertIsNone(reason)
        self.assertEqual(targets["transactionStatus"]["value"], "completed")
        for name in ("BOB. Transaction declined", "YOUR OWN ACCOUNT", "ME", "لَمْ تتم الحَوَالة"):
            child = {"text": "JOD 7.000 credited from " + name + ".", "expected_merchant": name}
            self.assertEqual(assess_guard(parent, child, reviewed)[0], "risky_changed_name_slot")

    def test_unmasked_negation_nonpositive_amount_and_new_event_held(self):
        parent = {"text": "JOD 5.000 credited to account *1111.", "expected_merchant": None}
        reviewed = {"annotations": {"transactionStatus": {"value": "completed", "evidence": [{"text": "credited"}]},
                                    "direction": {"value": "incoming", "evidence": [{"text": "credited"}]},
                                    "amount": {"evidence": [{"text": "5.000"}]}}}
        for text in ("JOD 7.000 not credited to account *2222.", "JOD 7.000 credited to account *2222. Purchase completed.",
                     "JOD 0.000 credited to account *2222.", "JOD -7.000 credited to account *2222."):
            self.assertIsNotNone(assess_guard(parent, {"text": text, "expected_merchant": None}, reviewed)[0])

    def test_party_initials_not_stripped_as_routing_prefix(self):
        value = frame({"text": "JOD 5.000 credited from AB SMITH.", "expected_merchant": "AB SMITH"})
        self.assertEqual(value["partySlot"], "ab smith")
        self.assertEqual(normalize_text("JO\\nJOD 5.000 credited"), "jod 5.000 credited")
        self.assertEqual(normalize_text("IF\nJOD 5.000 credited"), "if jod 5.000 credited")
        self.assertEqual(normalize_text("NO transaction completed"), "no transaction completed")

    def test_conflicting_duplicates_held_not_majority_voted(self):
        rows = [{"recordId": name, "sourceReviewRecordId": name, "sourceExpressionId": name,
                 "outcome": "candidate", "candidateTargets": {"transactionStatus": {"value": status}}}
                for name, status in (("a", "completed"), ("b", "non_transaction"))]
        deduplicate(rows, {"a": "same", "b": "same"})
        self.assertTrue(all(row["outcome"] == "hold" and not row["candidateTargets"] for row in rows))

    def test_target_or_admission_tampering_rejected(self):
        original = next(row for row in self.rows if row["outcome"] == "candidate")
        for change in ({"trainingEligible": True}, {"candidateTargets": {**original["candidateTargets"], "expenseCategory": {"value": "Food"}}}):
            rows = deepcopy(self.rows)
            next(row for row in rows if row["recordId"] == original["recordId"]).update(change)
            with self.assertRaises(ValueError):
                validate_proposals(rows, self.drafts, self.sources, self.reviewed)

    def test_sampling_weight_cannot_be_forged_as_certainty(self):
        for value in (True, 0, 2, float("nan")):
            rows = deepcopy(self.rows)
            candidate = next(row for row in rows if row["outcome"] == "candidate")
            candidate["candidateTargets"]["transactionStatus"]["proposedTrainingWeight"] = value
            with self.assertRaises(ValueError):
                validate_proposals(rows, self.drafts, self.sources, self.reviewed)
