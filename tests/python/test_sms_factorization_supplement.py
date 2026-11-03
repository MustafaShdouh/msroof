"""Training-only supplement selection and exact context/event scope evidence."""
from copy import deepcopy
import unittest

from training.corpus import factorization_supplement as supplement
from training.corpus import factorization_pilot as pilot
from training.transactions.completion_adaptation import prepare


class FactorizationSupplementTests(unittest.TestCase):
    def test_frozen_outputs_training_boundary_and_evidence(self):
        rows, report, outputs = supplement.build()
        for path, content in outputs.items():
            self.assertEqual(path.read_bytes(), content.encode("utf-8"))
        queue = pilot.read(supplement.QUEUE)
        source = {r["recordId"]:r for r in queue["rows"]}
        _, training, development, reserved = prepare()
        training_ids = {r["recordId"] for r in training}
        excluded = {r["recordId"] for cohort in development.values() for r in cohort} | {r["recordId"] for r in reserved}
        self.assertEqual(len(rows), 12)
        for row in rows:
            self.assertIn(row["recordId"], training_ids)
            self.assertNotIn(row["recordId"], excluded)
            for field in ("messageContext", "describedEventState"):
                for span in row[field]["evidence"]:
                    self.assertEqual(source[row["recordId"]]["text"][span["start"]:span["end"]], span["text"])
            self.assertFalse(row["trainingEligible"])
            self.assertFalse(row["modelFittingAllowed"])
        self.assertEqual(report["combinedReviewStateCounts"], {"reviewed_weak":35,"hold":1})
        self.assertEqual(report["missingReviewedContexts"], ["unknown"])

    def test_quoted_completion_keeps_nontransaction_target(self):
        rows, _, _ = supplement.build()
        for language in ("ar", "en"):
            actual = next(r for r in rows if r["recordId"] == f"scope-v1-pension-demo-1-{language}")
            quoted = next(r for r in rows if r["recordId"] == f"scope-v1-pension-demo-2-{language}")
            self.assertEqual(actual["describedEventState"]["value"], "completed")
            self.assertEqual(quoted["describedEventState"]["value"], "completed")
            self.assertEqual(actual["messageContext"]["value"], "financial_notice")
            self.assertEqual(quoted["messageContext"]["value"], "instruction_or_example")
            self.assertEqual(quoted["originalCompletionTarget"], "non_transaction")

    def test_source_fold_or_membership_change_rejected(self):
        _, training, _, _ = prepare()
        original = pilot.read(pilot.QUEUE)
        manifest = pilot.read(supplement.SOURCE_MANIFEST)
        changed = deepcopy(manifest)
        for group in changed["families"]:
            if group["theme"] == "illustrative_scope":
                group["fold"] = "reserved_diagnostic"
        with self.assertRaises(ValueError):
            supplement.selection(training, original, changed)
        chosen, _ = supplement.selection(training, original, manifest)
        missing = [r for r in training if r["recordId"] != chosen[0]["recordId"]]
        with self.assertRaises(ValueError):
            supplement.selection(missing, original, manifest)


if __name__ == "__main__":
    unittest.main()
