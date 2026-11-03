"""Training-only selection, exact evidence and non-conflation safeguards."""
from copy import deepcopy
import unittest

from training.corpus.factorization_pilot import build, selection, span, validate_review, read, CONTRACT, QUEUE, REVIEWS
from training.transactions.completion_adaptation import prepare


class FactorizationPilotTests(unittest.TestCase):
    def test_final_sidecars_and_admission_boundaries(self):
        annotations, audit, outputs = build()
        for path, expected in outputs.items():
            self.assertEqual(path.read_bytes(), expected.encode("utf-8"))
        self.assertEqual(audit["structurallyInventoriedGroups"], 129)
        self.assertEqual(audit["semanticallyFullyReviewedGroups"], 0)
        self.assertEqual(audit["pilotReviewStateCounts"], {"reviewed_weak":23,"hold":1})
        self.assertEqual(audit["mixedTargetGroups"], 28)
        self.assertIn("instruction_or_example", audit["missingReviewedContexts"])
        for row in annotations:
            self.assertFalse(row["trainingEligible"])
            self.assertFalse(row["independentEvaluationEligible"])
            self.assertFalse(row["modelFittingAllowed"])

    def test_selection_is_label_and_order_independent(self):
        _, training, _, _ = prepare()
        _, original = selection(training)
        altered = [{**r,"target":"arbitrary_label_for_selection_test","weight":99} for r in reversed(training)]
        _, changed = selection(altered)
        self.assertEqual([r["recordId"] for r in original], [r["recordId"] for r in changed])
        self.assertEqual(len({r["group"] for r in original}), 24)

    def test_described_completion_does_not_overwrite_transaction_truth(self):
        rows, _, _ = build()
        claim = next(r for r in rows if r["recordId"] == "scope-v1-rent-share-2-en")
        self.assertEqual(claim["messageContext"]["value"], "personal_conversation")
        self.assertEqual(claim["describedEventState"]["value"], "completed")
        self.assertEqual(claim["originalCompletionTarget"], "non_transaction")
        balance = next(r for r in rows if r["recordId"] == "synthetic-v1-0121")
        self.assertEqual(balance["describedEventState"]["value"], "no_event")

    def test_evidence_and_hold_integrity(self):
        text = "📩 قُيِّدَ المبلغ."
        evidence = span(text, "قُيِّدَ")
        self.assertEqual(evidence["start"], 2)
        self.assertEqual(text[evidence["start"]:evidence["end"]], "قُيِّدَ")
        with self.assertRaises(ValueError): span(text, "قيد")
        queue, reviews = read(QUEUE), read(REVIEWS)
        review = deepcopy(reviews["reviews"][1])
        review["holdReasons"] = []
        with self.assertRaises(ValueError):
            validate_review(queue["rows"][1], review, read(CONTRACT))


if __name__ == "__main__":
    unittest.main()
