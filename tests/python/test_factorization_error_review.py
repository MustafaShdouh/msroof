"""Analysis safeguards: paired changes, duplicate controls and masked errors."""
import unittest
from tools.evaluation.review_sms_factorization_errors import transition, unique_counts, component_substitution


class ErrorReviewTests(unittest.TestCase):
    def test_equal_accuracy_can_hide_opposite_case_swaps(self):
        self.assertEqual(transition("non_transaction", "non_transaction", "completed"), "regression")
        self.assertEqual(transition("non_transaction", "completed", "non_transaction"), "fix")
        self.assertEqual(transition("uncertain", "completed", "non_transaction"), "both_wrong")

    def test_duplicate_quote_control_does_not_add_another_error(self):
        row = dict(textSha256="same", target="non_transaction", direct="non_transaction",
                   factorized="completed", transition="regression")
        self.assertEqual(unique_counts([row, dict(row)]), {"regression": 1})
        with self.assertRaises(AssertionError):
            unique_counts([row, dict(row, target="completed")])

    def test_correct_status_does_not_imply_correct_components(self):
        row = dict(target="non_transaction", factorized="non_transaction",
                   context="instruction_or_example", event="not_completed",
                   goldContext="financial_notice", goldEvent="not_completed")
        result = component_substitution([row])
        self.assertEqual(result["savedStatusCorrect"], 1)
        self.assertEqual(result["bothFieldsCorrect"], 0)
        self.assertEqual(result["wrongFieldButStatusCorrect"], 1)
