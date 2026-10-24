"""Verify prospective holdout boundaries without claiming evaluation accuracy."""

import copy
import json
import unittest

from training import prepare_category_evaluation as evaluation


def business(key, name, aliases=None, group=None):
    return {"businessId": key, "name": name, "aliases": aliases or [], "brandGroup": group or key,
            "labelStatus": "needs_review", "humanConfirmedCategory": None}


class CategoryEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.rows = [business(str(i), f"Business{i}", [f"متجر{i}"] if i < 20 else []) for i in range(100)]

    def test_deterministic_and_input_order_independent(self):
        self.assertEqual(evaluation.prepare(self.rows), evaluation.prepare(list(reversed(self.rows))))
        assignments = evaluation.prepare(self.rows)["businessAssignments"]
        self.assertEqual({fold: list(assignments.values()).count(fold) for fold in evaluation.FOLDS},
                         {"train": 70, "validation": 15, "test": 15})

    def test_arabic_strata_have_validation_and_test_coverage(self):
        assignments = evaluation.prepare(self.rows)["businessAssignments"]
        self.assertEqual({fold: sum(assignments[str(i)] == fold for i in range(20)) for fold in evaluation.FOLDS},
                         {"train": 14, "validation": 3, "test": 3})

    def test_alias_and_existing_brand_groups_stay_together(self):
        rows = self.rows + [business("arabic", "متجر0"), business("branch", "Unrelated Display", group="0")]
        plan = evaluation.prepare(rows)
        self.assertEqual(len({plan["businessAssignments"][key] for key in ("0", "arabic", "branch")}), 1)
        groups = evaluation.identity_groups(rows)
        self.assertEqual(len({groups[key] for key in ("0", "arabic", "branch")}), 1)

    def test_whole_token_prefix_is_conservative_not_character_prefix(self):
        rows = [business("a", "ZARA"), business("b", "ZARA Home"),
                business("c", "ALDO"), business("d", "Al Domary Restaurant"),
                business("e", "Alma"), business("f", "Al Maseyah Pharmacy")]
        groups = evaluation.identity_groups(rows)
        self.assertEqual(groups["a"], groups["b"])
        self.assertNotEqual(groups["c"], groups["d"])
        self.assertNotEqual(groups["e"], groups["f"])

    def test_labels_and_new_aliases_do_not_reshuffle_existing_plan(self):
        plan = evaluation.prepare(self.rows)
        changed = copy.deepcopy(self.rows)
        changed[-1]["aliases"].append("متجر جديد")
        changed[0].update(labelStatus="human_reviewed_merchant_default", humanConfirmedCategory="Food")
        self.assertEqual(evaluation.prepare(changed, plan)["businessAssignments"], plan["businessAssignments"])

    def test_new_overlap_across_frozen_folds_fails(self):
        plan = evaluation.prepare(self.rows)
        left = next(row for row in self.rows if plan["businessAssignments"][row["businessId"]] == "train")
        right = next(row for row in self.rows if plan["businessAssignments"][row["businessId"]] == "test")
        changed = copy.deepcopy(self.rows)
        next(row for row in changed if row["businessId"] == right["businessId"])["aliases"].append(left["name"])
        with self.assertRaisesRegex(ValueError, "crosses frozen folds"):
            evaluation.prepare(changed, plan)

    def test_changed_membership_duplicate_ids_and_bad_assignments_fail(self):
        plan = evaluation.prepare(self.rows)
        with self.assertRaises(ValueError):
            evaluation.prepare(self.rows[:-1], plan)
        with self.assertRaises(ValueError):
            evaluation.prepare(self.rows + [self.rows[0]])
        invalid = copy.deepcopy(plan)
        invalid["businessAssignments"]["0"] = "unknown"
        with self.assertRaises(ValueError):
            evaluation.prepare(self.rows, invalid)

    def test_source_proposals_never_become_gold_or_accuracy(self):
        plan = evaluation.prepare(self.rows)
        self.rows[0]["humanConfirmedCategory"] = "Food"  # Not reviewed.
        report = evaluation.readiness(self.rows, plan, ["Food", "Fees"])
        self.assertEqual(sum(row["humanReviewedMerchantDefaults"] for row in report["folds"].values()), 0)
        self.assertFalse(report["categoryModelReady"])
        self.assertFalse(report["independentSmsEvaluationReady"])
        self.assertIsNone(report["accuracy"])

    def test_assistant_labels_are_counted_separately_from_human_gold(self):
        plan = evaluation.prepare(self.rows)
        self.rows[0].update(labelStatus="assistant_reviewed_merchant_default", assistantReviewedCategory="Food")
        report = evaluation.readiness(self.rows, plan, ["Food"])
        self.assertEqual(sum(row["assistantReviewedMerchantDefaults"] for row in report["folds"].values()), 1)
        self.assertEqual(sum(row["humanReviewedMerchantDefaults"] for row in report["folds"].values()), 0)
        self.assertIsNone(report["accuracy"])

    def test_real_corpus_plan_covers_every_business_without_overlap(self):
        rows = [json.loads(line) for line in evaluation.BUSINESSES.read_text(encoding="utf-8").splitlines()]
        saved = json.loads(evaluation.PLAN.read_text(encoding="utf-8"))
        self.assertEqual(len(saved["businessAssignments"]), 200)
        self.assertEqual(evaluation.prepare(rows, saved), saved)
        for members in saved["leakageGroups"].values():
            self.assertEqual(len({saved["businessAssignments"][key] for key in members}), 1)


if __name__ == "__main__":
    unittest.main()
