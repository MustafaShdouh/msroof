"""Bilingual factual/hypothetical contrasts and conservative ownership handling."""
import unittest

from training.evaluation.arabic_semantics import evaluate_semantics
from tests.python.nontransaction_review import evaluate_pairs_with_review as evaluate_pairs


class ArabicMessageSemanticsTests(unittest.TestCase):
    def test_completion_direction_and_context_in_three_runtimes(self):
        report = evaluate_semantics()
        self.assertEqual(report["authoredTexts"], 45)
        self.assertEqual(report["bodyComparisons"], 135)
        self.assertEqual(report["wrapperComparisons"], 540)
        self.assertEqual(report["legacyUnchangedThreeRuntimeComparisons"], 135)

    def test_previous_arabic_inclusion_findings_are_resolved(self):
        report, _ = evaluate_pairs()
        self.assertEqual(report["retainedMessageOnlyInclusionsAmongUnrecognizedControls"], {})
