"""Residual measures must count deferrals, partial truth and false certainty."""
import unittest
from tools.evaluation.assess_core_money_residuals import counts


class CoreResidualTests(unittest.TestCase):
    def test_deferrals_and_wrong_certainty_are_not_correct(self):
        rows=[dict(expected=dict(transactionStatus='completed'),actual=dict(transactionStatus='uncertain',trackingDecision='review')),
              dict(expected=dict(transactionStatus='non_transaction'),actual=dict(transactionStatus='completed',trackingDecision='review')),
              dict(expected=dict(transactionStatus='uncertain'),actual=dict(transactionStatus='non_transaction',trackingDecision='exclude'))]
        result=counts(rows)
        self.assertEqual(result['missedCompletion'],1)
        self.assertEqual(result['falseCompleted'],1)
        self.assertEqual(result['falseIncludes'],0)
        self.assertEqual(result['wrongCertainty'],1)
        self.assertEqual(result['statusCorrect'],0)

    def test_missing_truth_stays_unscored(self):
        result=counts([dict(expected=dict(amount=None),actual=dict(amount=None,transactionStatus='uncertain',trackingDecision='review'))])
        self.assertEqual(result['statusCheckedCases'],0)
        self.assertEqual(result['allAssertedFieldsCorrect'],1)
        self.assertNotIn('direction',result['fields'])
        self.assertEqual(result['endToEndEligible'],0)

    def test_end_to_end_counts_all_eligible_not_only_accepted(self):
        expected=dict(transactionStatus='completed',trackingDecision='include',amount=12,currency='JOD',direction='incoming')
        result=counts([dict(expected=expected,actual=dict(expected,trackingDecision='review'))])
        self.assertEqual(result['endToEndEligible'],1)
        self.assertEqual(result['endToEndCorrect'],0)
