"""Check missing-class, provenance and lexical-overlap audit behavior."""

import copy
import unittest

from training.categories import audit as auditor
from training.categories.split import prepare


class CategoryAuditTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{"businessId": str(i), "brandGroup": str(i), "name": f"Store{i}", "aliases": [],
                      "labelStatus": "human_reviewed_merchant_default", "humanConfirmedCategory": "Food",
                      "assistantReviewedCategory": None} for i in range(30)]
        self.plan = prepare(self.rows)

    def test_evaluation_only_category_is_not_solved_by_holdout_labels(self):
        row = next(row for row in self.rows if self.plan["businessAssignments"][row["businessId"]] == "test")
        row["humanConfirmedCategory"] = "Transportation"
        result = auditor.audit(self.rows, self.plan, ["Food", "Transportation"], [])
        self.assertIn("Transportation", result["missingTrainingCategories"])
        self.assertEqual(result["evaluationOnlyCategories"]["test"], ["Transportation"])
        self.assertFalse(result["full15CategoryTrainingReady"])

    def test_assistant_and_human_counts_remain_separate(self):
        row = self.rows[0]
        row.update(labelStatus="assistant_reviewed_merchant_default", humanConfirmedCategory=None, assistantReviewedCategory="Food")
        result = auditor.audit(self.rows, self.plan, ["Food"], [])
        counts = result["folds"][self.plan["businessAssignments"][row["businessId"]]]["categoryCounts"]
        self.assertEqual(counts["assistant"]["Food"], 1)
        self.assertEqual(counts["combined"]["Food"], counts["human"]["Food"] + 1)

    def test_proposed_or_unresolved_labels_do_not_count(self):
        self.rows[0]["labelStatus"] = "needs_review"
        result = auditor.audit(self.rows, self.plan, ["Food"], [])
        self.assertEqual(result["labeledBusinesses"], 29)
        self.assertEqual(result["unresolvedBusinesses"], [self.rows[0]["name"]])

    def test_cross_fold_family_is_flagged_without_moving_assignments(self):
        names = [next(row["name"] for row in self.rows if self.plan["businessAssignments"][row["businessId"]] == fold) for fold in ("train", "test")]
        before = copy.deepcopy(self.plan)
        family = {"familyId": "related", "members": names, "url": "https://example.org/", "evidence": "Test family evidence"}
        result = auditor.audit(self.rows, self.plan, ["Food"], [family])
        self.assertEqual(result["knownFamilyCrossFoldConflicts"], 1)
        self.assertEqual(self.plan, before)

    def test_unknown_family_identity_and_unsupported_category_fail(self):
        with self.assertRaises(ValueError):
            auditor.audit(self.rows, self.plan, ["Food"], [{"members": ["Unknown"]}])
        self.rows[0]["humanConfirmedCategory"] = "Invented"
        with self.assertRaises(ValueError):
            auditor.audit(self.rows, self.plan, ["Food"], [])

    def test_alias_leak_across_folds_is_rejected(self):
        training = next(row for row in self.rows if self.plan["businessAssignments"][row["businessId"]] == "train")
        heldout = next(row for row in self.rows if self.plan["businessAssignments"][row["businessId"]] == "test")
        heldout["aliases"].append(training["name"])
        with self.assertRaisesRegex(ValueError, "crosses frozen folds"):
            auditor.audit(self.rows, self.plan, ["Food"], [])

    def test_lexical_scan_uses_word_sequences_and_excludes_training_names(self):
        rows = [{"businessId": "one", "name": "Max", "aliases": []},
                {"businessId": "two", "name": "Coffee House", "aliases": ["مقهى القهوة"]},
                {"businessId": "three", "name": "Training Shop", "aliases": []}]
        plan = {"businessAssignments": {"one": "test", "two": "validation", "three": "train"}}
        result = auditor.historical_mentions(rows, plan, {"corpus": [
            {"id": "substring", "body": "Purchase at Hypermax"},
            {"id": "exact", "text": "Purchase at MAX and coffee house"},
            {"id": "arabic", "body": "شراء من مَقهى القهوة"},
            {"id": "train", "body": "Paid at Training Shop"}]})["corpora"]["corpus"]
        self.assertEqual(result["matchingRecordCount"], 2)
        self.assertEqual(result["potentialHeldoutBusinessMentions"], {"one": ["exact"], "two": ["exact", "arabic"]})

    def test_augmentation_remains_bounded_and_planned(self):
        result = auditor.audit(self.rows, self.plan, ["Food"], [])
        policy = result["augmentationPolicy"]
        self.assertEqual(policy["maxSyntheticExtraFormsPerTrainingBusiness"], 1)
        self.assertIn("bounded_training_protocol", policy["status"])
        self.assertEqual(policy["trainingBusinessLimit"], result["folds"]["train"]["labeledBusinesses"])

    def test_class_presence_does_not_certify_full_model_readiness(self):
        result = auditor.audit(self.rows, self.plan, ["Food"], [])
        self.assertTrue(result["allTargetCategoriesRepresentedInTraining"])
        self.assertFalse(result["full15CategoryTrainingReady"])


if __name__ == "__main__":
    unittest.main()
