"""Independent-event and uncertainty contrasts for the bounded transfer repair."""
import unittest

from tests.python.nontransaction_review import evaluate_pairs_with_review as evaluate_pairs


class PairedMovementTests(unittest.TestCase):
    def test_bilingual_events_negatives_and_confirmations_in_three_runtimes(self):
        report, _ = evaluate_pairs()
        self.assertEqual(report["authoredTexts"], 39)
        self.assertEqual(report["recognizedTexts"], 10)
        self.assertEqual(report["bodyComparisons"], 117)
        self.assertEqual(report["wrapperComparisons"], 468)
        self.assertEqual(report["legacyThreeRuntimeComparisons"], 117)
