"""Target-contract safeguards, deliberately independent of model inference."""
import copy
import json
import unittest

from tools.contracts import validate_transaction_behavior as behavior


class TransactionBehaviorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = behavior.load_contract()
        cls.bundle = json.loads(behavior.CASES_PATH.read_text(encoding="utf-8"))

    def case(self, key):
        return copy.deepcopy(next(x["expected"] for x in self.bundle["cases"] if x["id"] == key))

    def test_authored_bundle_and_exact_human_decisions_validate_without_mutation(self):
        original = copy.deepcopy(self.bundle)
        behavior.validate_bundle(self.bundle, self.contract)
        self.assertEqual(self.bundle, original)
        self.assertEqual({x["language"] for x in self.bundle["cases"]}, {"arabic", "english", "mixed"})

    def test_bad_version_or_unknown_field_fails(self):
        for mutation in ({"contractVersion": "2.0.0"}, {"confidence": 1.0}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                behavior.validate_result(self.case("purchase_balance_separation") | mutation)

    def test_invalid_money_is_never_accepted(self):
        for amount in (True, "12.50", 0, -1, float("nan"), float("inf"), 10 ** 400):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                behavior.validate_result(self.case("purchase_balance_separation") | {"amount": amount})

    def test_default_currency_is_marked_and_explicit_foreign_currency_preserved(self):
        for key in ("default_missing_currency", "default_ambiguous_currency"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                behavior.validate_result(self.case(key) | {"currency": "USD"})
        behavior.validate_result(self.case("explicit_foreign_currency"))

    def test_transfer_ownership_cannot_be_silently_changed_to_inclusion(self):
        for key in ("own_accounts_english", "own_accounts_arabic", "two_masks_unknown_ownership"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                behavior.validate_result(self.case(key) | {"trackingDecision": "include"})
        for key in ("p2p_outgoing", "p2p_incoming", "arabic_p2p_outgoing"):
            behavior.validate_result(self.case(key))

    def test_completed_missing_fields_remains_completed_and_requires_review(self):
        for key in ("completed_missing_amount", "completed_ambiguous_amount", "completed_unknown_direction"):
            result = self.case(key)
            self.assertEqual(result["transactionStatus"], "completed")
            self.assertEqual(result["trackingDecision"], "review")
            with self.subTest(key=key), self.assertRaises(ValueError):
                behavior.validate_result(result | {"trackingDecision": "include"})

    def test_unclear_completion_cannot_be_auto_recorded(self):
        with self.assertRaises(ValueError):
            behavior.validate_result(self.case("completion_unclear") | {"trackingDecision": "include"})

    def test_incoming_excluded_and_uncertain_events_cannot_emit_expense_labels(self):
        for key in ("p2p_incoming", "own_accounts_english", "completion_unclear", "otp_not_completed"):
            result = self.case(key) | {"expenseCategory": "Food", "categoryStatus": "assigned"}
            with self.subTest(key=key), self.assertRaises(ValueError):
                behavior.validate_result(result)

    def test_other_and_uncertain_are_distinct(self):
        behavior.validate_result(self.case("understood_other_expense"))
        with self.assertRaises(ValueError):
            behavior.validate_result(self.case("opaque_merchant_category") | {"expenseCategory": "Other"})
        with self.assertRaises(ValueError):
            behavior.validate_result(self.case("purchase_balance_separation") | {"expenseCategory": "Utilities & Bills"})

    def test_reasons_cannot_hide_missing_amount_or_ownership(self):
        for key in ("completed_missing_amount", "two_masks_unknown_ownership"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                behavior.validate_result(self.case(key) | {"reasonCodes": ["completed_transaction"]})

    def test_policy_examples_cannot_be_admitted_as_training_or_independent_evaluation(self):
        for field in ("trainingEligible", "evaluationEligible"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                behavior.validate_bundle(self.bundle | {field: True})
        bundle = copy.deepcopy(self.bundle)
        bundle["cases"][0]["labelSource"] = "human_reviewed_real_sms"
        with self.assertRaises(ValueError):
            behavior.validate_bundle(bundle)

    def test_exact_human_policy_text_label_and_scope_are_protected(self):
        for field, value in (("text", "changed"), ("expectedCategory", "Other"), ("scope", "all_merchant_payments")):
            bundle = copy.deepcopy(self.bundle)
            bundle["reviewedCategoryPolicies"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                behavior.validate_bundle(bundle)

    def test_sender_metadata_and_timestamp_validation(self):
        behavior.validate_input({"text": "", "sender": None, "isContact": True, "receivedAt": "2026-10-25T12:00:00+03:00"}, self.contract)
        for value in ({"sender": "BANK"}, {"text": 42}, {"text": "x", "isContact": 1},
                      {"text": "x", "receivedAt": "2026-10-25T12:00:00"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                behavior.validate_input(value, self.contract)


if __name__ == "__main__":
    unittest.main()
