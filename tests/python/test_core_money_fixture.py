"""Validate the new development pack without requiring existing gaps to pass."""
import json
import unittest
from tools.evaluation.core_money import FIXTURE,FIELDS,equal,field_errors


class CoreMoneyFixtureTests(unittest.TestCase):
    def test_provenance_coverage_and_pending_cases(self):
        fixture=json.loads(FIXTURE.read_text(encoding="utf-8"));cases=fixture["cases"]
        self.assertEqual(len(cases),52)
        self.assertEqual(len({c["id"] for c in cases}),52)
        self.assertEqual({c["language"] for c in cases},{"en","ar","mixed"})
        self.assertFalse(fixture["trainingEligible"])
        for row in cases:
            self.assertFalse(row["independentEvaluationEligible"])
            self.assertFalse(row["trainingEligible"])
            self.assertTrue(set(row["expected"])<=set(FIELDS))
        self.assertEqual(len(fixture["pendingPolicyCases"]),4)
        self.assertTrue(all("expected" not in c for c in fixture["pendingPolicyCases"]))

    def test_exact_money_not_tolerance_or_boolean_coercion(self):
        self.assertTrue(equal("amount",12.750,12.75))
        self.assertFalse(equal("amount",12.751,12.75))
        self.assertFalse(equal("amount",True,1))
        self.assertFalse(equal("amount",float("nan"),1))
        self.assertTrue(equal("amount",None,None))
        self.assertTrue(field_errors({}, {"amount":None}))
        self.assertFalse(field_errors({"amount":None},{"amount":None}))
