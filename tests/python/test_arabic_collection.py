"""Prepared metadata must add identities while reserving all original folds."""
import copy
import json
import unittest
from training import prepare_arabic_collection as collection
from training import prepare_merchant_training_extension as extension


class ArabicCollectionTests(unittest.TestCase):
    def setUp(self):
        self.base = [json.loads(line) for line in extension.BASE.read_text(encoding="utf-8").splitlines()]
        self.plan = json.loads(extension.SPLIT.read_text(encoding="utf-8"))
        self.allowed = json.loads(extension.TAXONOMY.read_text(encoding="utf-8"))["allowedCategories"]
        self.prior = json.loads(extension.SOURCE.read_text(encoding="utf-8"))["businesses"] + json.loads(collection.ROUND3.read_text(encoding="utf-8"))["businesses"]
        self.incoming = json.loads(collection.SOURCE.read_text(encoding="utf-8"))["businesses"]

    def test_deterministic_distinct_arabic_train_only_records(self):
        before = copy.deepcopy(self.plan)
        rows = collection.prepare_collection(self.base, self.plan, self.allowed, self.prior, self.incoming)
        reverse = collection.prepare_collection(self.base, self.plan, self.allowed, list(reversed(self.prior)), list(reversed(self.incoming)))
        self.assertEqual(rows, reverse)
        self.assertEqual(self.plan, before)
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(row["fold"] == "train" and not row["evaluationEligible"] and
                            row["humanConfirmedCategory"] is None and row["reviewerType"] == "assistant" and
                            any('\u0621' <= c <= '\u064a' for c in row["name"]) for row in rows))

    def test_prior_duplicate_and_reserved_alias_are_rejected(self):
        with self.assertRaises(ValueError):
            collection.prepare_collection(self.base, self.plan, self.allowed, self.prior, [self.prior[0]])
        heldout = next(row for row in self.base if self.plan["businessAssignments"][row["businessId"]] == "test")
        record = self.incoming[0] | {"aliases": [heldout["name"]]}
        with self.assertRaises(ValueError):
            collection.prepare_collection(self.base, self.plan, self.allowed, self.prior, [record])

    def test_documentation_never_claims_completed_sms_or_evaluation_truth(self):
        evidence = json.loads((collection.ROOT / "data/sources/transactions/jordan_context_evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["localRawProvenance"]["reportedOriginalSeedCountsApproximate"], {"Arab Bank": 20, "Capital Bank": 10})
        self.assertTrue(all(row["sourceKind"] == "official_service_documentation_not_sms" and
                            not row["trainingEligible"] and not row["evaluationEligible"] and
                            row["smsText"] is None and row["isCompletedTransaction"] is None for row in evidence["records"]))


if __name__ == "__main__":
    unittest.main()
