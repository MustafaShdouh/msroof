"""Protect evaluation denominators, missing evidence, exact values and parity."""
import copy
import json
import unittest

from training import evaluate_behavior as evaluation


class BehaviorEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, bundle, _, _ = evaluation.load_inputs()
        cls.cases = {case["id"]: case for case in bundle["cases"]}
        cls.categories = evaluation.load_contract()["categories"]

    def accepted(self, case_id, **changes):
        expected = self.cases[case_id]["expected"]
        return {"result": {"isValidTransaction": True, "data": {
            "amount": expected["amount"], "currency": expected["currency"],
            "direction": {"incoming": "INCOMING", "outgoing": "OUTGOING"}.get(expected["direction"]),
            "category": "General & Uncategorized", **changes}}}

    def test_decimal_exactness_does_not_accept_a_small_wrong_amount(self):
        self.assertTrue(evaluation.money_equal(12.5, 12.500))
        for value in (12.5001, True, "12.5", float("nan"), float("inf")):
            self.assertFalse(evaluation.money_equal(12.5, value))

    def test_zero_denominator_is_unmeasurable(self):
        self.assertEqual(evaluation.ratio(0, 0)["rate"], None)

    def test_all_eligible_metrics_penalize_missed_transactions(self):
        ids = ["purchase_balance_separation", "p2p_incoming"]
        outputs = {ids[0]: self.accepted(ids[0]), ids[1]: {"result": {"isValidTransaction": False, "data": None}}}
        report = evaluation.policy_metrics([self.cases[key] for key in ids], outputs, self.categories)
        self.assertEqual(report["amountCurrencyAllEligible"]["rate"], .5)
        self.assertEqual(report["amountCurrencyAcceptedEligible"]["rate"], 1)
        self.assertEqual(report["eligibleMissOrReview"]["rate"], .5)

    def test_false_inclusion_uses_all_negative_messages_not_all_assignments(self):
        ids = ["purchase_balance_separation", "payment_request", "declined_not_completed"]
        outputs = {ids[0]: self.accepted(ids[0]), ids[1]: self.accepted(ids[1]),
                   ids[2]: {"result": {"isValidTransaction": False, "data": None}}}
        report = evaluation.policy_metrics([self.cases[key] for key in ids], outputs, self.categories)
        self.assertEqual(report["ordinaryFalseInclusion"]["total"], 2)
        self.assertEqual(report["ordinaryFalseInclusion"]["rate"], .5)

    def test_rejection_is_not_guessed_to_mean_review_or_no_completion(self):
        case = self.cases["completed_missing_amount"]
        outputs = {case["id"]: {"result": {"isValidTransaction": False, "data": None}}}
        report = evaluation.policy_metrics([case], outputs, self.categories)
        self.assertEqual(report["trackingDecisionConfusion"]["review"]["exclude"], 1)
        self.assertEqual(report["completionStatusConfusion"]["completed"]["unsupported"], 1)

    def test_legacy_category_is_unsupported_not_a_silent_mapping_or_abstention(self):
        key = "purchase_balance_separation"
        outputs = {key: self.accepted(key, category="Dining & Food Delivery")}
        report = evaluation.policy_metrics([self.cases[key]], outputs, self.categories)["category"]
        self.assertEqual(report["legacyClaimedAssignments"], 1)
        self.assertEqual(report["unsupportedTaxonomyAssignments"], 1)
        self.assertEqual(report["canonicalCoverage"]["rate"], 0)
        self.assertIsNone(report["canonicalAnsweredAgreement"]["rate"])

    def test_aliases_are_validated_and_other_fields_remain_in_parity(self):
        original = {"data": {"merchantOrParty": "FULL", "merchant_or_party": "FULL", "originalAmount": 3, "custom": 7}}
        before = copy.deepcopy(original)
        canonical = evaluation.canonical_result(original)
        self.assertEqual(original, before)
        self.assertEqual(canonical["data"], {"merchantOrParty": "FULL", "originalAmount": 3, "custom": 7})
        bad = copy.deepcopy(original)
        bad["data"]["merchant_or_party"] = "WRONG"
        with self.assertRaises(ValueError):
            evaluation.canonical_result(bad)
        self.assertEqual(evaluation.differences(canonical, {"data": {"merchantOrParty": "FULL"}}), ["data.custom", "data.originalAmount"])

    def test_strict_party_values_never_use_substring_acceptance(self):
        cases = [{"id": "strict", "expected": {"isValidTransaction": True, "merchantOrParty": "FULL SHOP"}}]
        outputs = {"strict": {"result": {"isValidTransaction": True, "data": {"merchantOrParty": "SHOP"}}}}
        report = evaluation.regression_metrics(cases, outputs)
        self.assertEqual(report["fieldValues"]["merchantOrParty"]["allEligible"]["rate"], 0)

    def test_conformance_data_stays_unadmitted(self):
        path = evaluation.ROOT / "tests/fixtures/transaction_behavior_cases.json"
        before = path.read_bytes()
        evaluation.load_inputs()
        bundle = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(bundle["trainingEligible"])
        self.assertFalse(bundle["evaluationEligible"])
        self.assertEqual(before, path.read_bytes())


if __name__ == "__main__":
    unittest.main()
