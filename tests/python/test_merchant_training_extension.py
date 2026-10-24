"""Training-only additions must preserve identities, evidence and reservations."""

import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock
from unittest.mock import patch

from training import prepare_merchant_training_extension as extension
from training import train_merchant_category as trainer


class MerchantTrainingExtensionTests(unittest.TestCase):
    def setUp(self):
        self.base = [json.loads(line) for line in extension.BASE.read_text(encoding="utf-8").splitlines()]
        self.plan = json.loads(extension.SPLIT.read_text(encoding="utf-8"))
        self.allowed = json.loads(extension.TAXONOMY.read_text(encoding="utf-8"))["allowedCategories"]
        self.records = json.loads(extension.SOURCE.read_text(encoding="utf-8"))["businesses"]

    def validate(self, records):
        return extension.validate_extension(records, self.base, self.plan, self.allowed)

    def test_real_extension_deterministic_training_only_and_no_split_mutation(self):
        original = copy.deepcopy(self.plan)
        rows = self.validate(self.records)
        self.assertEqual(rows, self.validate(list(reversed(self.records))))
        self.assertEqual(len(rows), 15)
        self.assertEqual(self.plan, original)
        self.assertTrue(all(row["fold"] == "train" and not row["evaluationEligible"] and
                            row["reviewerType"] == "assistant" and row["humanConfirmedCategory"] is None for row in rows))

    def test_training_admission_preserves_holdouts_and_business_weight(self):
        original = copy.deepcopy(self.plan)
        rows, plan, paths = trainer.with_training_extension(self.base, self.plan, self.allowed)
        self.assertEqual(self.plan, original)
        self.assertEqual(len(paths), 2)
        for key, fold in self.plan["businessAssignments"].items():
            self.assertEqual(plan["businessAssignments"][key], fold)
        for variant in trainer.VARIANTS:
            groups = trainer.training_views(rows, plan, variant)
            self.assertEqual(len(groups), 156)
            self.assertEqual(len({group[0]["category"] for group in groups}), 12)
            self.assertTrue(all(plan["businessAssignments"][group[0]["businessId"]] == "train" for group in groups))
            self.assertTrue(all(abs(sum(view["businessWeight"] for view in group) - 1) < 1e-12 for group in groups))
        with self.assertRaisesRegex(ValueError, "separate --run-id"):
            trainer.main(include_extension=True)

    def test_reserved_canonical_alias_feature_and_prefix_collisions_rejected(self):
        reserved = next(row for row in self.base if self.plan["businessAssignments"][row["businessId"]] == "test")
        for name in (reserved["name"], reserved["name"] + " Branch"):
            record = copy.deepcopy(self.records[0])
            record.update(name=name, aliases=[])
            with self.assertRaises(ValueError):
                self.validate([record])
        record = copy.deepcopy(self.records[0])
        record["aliases"] = [reserved["name"]]
        with self.assertRaises(ValueError):
            self.validate([record])

    def test_additional_collection_is_train_only_and_all_sources_are_hashed(self):
        path = extension.ROOT / "data/sources/businesses/jordan_training_round3.json"
        rows, plan, paths = trainer.with_training_extension(self.base, self.plan, self.allowed, path)
        self.assertIn(path, paths)
        self.assertEqual(len(paths), 3)
        self.assertEqual(len({row["businessId"] for row in rows}), len(self.base) + 25)
        self.assertTrue(all(plan["businessAssignments"][row["businessId"]] == "train" and not row["evaluationEligible"]
                            for row in rows[len(self.base):]))
        groups = trainer.training_views(rows, plan, "aliases")
        self.assertEqual(len(groups), 166)
        self.assertEqual(sum(group[0]["category"] == "Groceries" for group in groups), 13)
        self.assertEqual(sum(group[0]["category"] == "Health" for group in groups), 8)
        for key, fold in self.plan["businessAssignments"].items():
            self.assertEqual(plan["businessAssignments"][key], fold)
        fake = Mock()
        fake.read_text.return_value = json.dumps({"businesses": [self.records[0]]})
        with self.assertRaisesRegex(ValueError, "Duplicate extension identity"):
            trainer.with_training_extension(self.base, self.plan, self.allowed, fake)
        with self.assertRaisesRegex(ValueError, "requires --include-extension"):
            trainer.main("invalid", additional_source=path)

    def test_missing_evidence_and_false_human_provenance_rejected(self):
        for change in ({"sources": []}, {"reviewerType": "human"}, {"notes": ""},
                       {"geographicScope": "Other"}, {"sources": [{"url": "https://example.com"}]}):
            with self.assertRaises(ValueError):
                self.validate([self.records[0] | change])

    def test_context_categories_and_duplicate_identities_rejected(self):
        for category in extension.CONTEXT_ONLY:
            with self.assertRaises(ValueError):
                self.validate([self.records[0] | {"category": category}])
        with self.assertRaises(ValueError):
            self.validate([self.records[0], self.records[0]])

    def test_historical_inputs_snapshot_matches_original_report(self):
        report = json.loads(trainer.REPORT.read_text(encoding="utf-8"))
        snapshot = extension.ROOT / "data/training/snapshots/merchant_category_research_v1"
        for relative, expected in report["inputSha256"].items():
            self.assertEqual(hashlib.sha256((snapshot / relative).read_bytes()).hexdigest(), expected)
        self.assertNotEqual(hashlib.sha256(extension.BASE.read_bytes()).hexdigest(),
                            report["inputSha256"][str(extension.BASE.relative_to(extension.ROOT))])
        for variant in report["variants"].values():
            self.assertEqual(hashlib.sha256((extension.ROOT / variant["modelPath"]).read_bytes()).hexdigest(),
                             variant["modelSha256"])

    def test_output_guard_rejects_changed_inputs_before_overwrite(self):
        with patch.object(trainer, "fit") as fit:
            with self.assertRaisesRegex(ValueError, "new --run-id"):
                trainer.main()
            fit.assert_not_called()
        path = Mock()
        path.exists.return_value = True
        for saved in ({"inputSha256": {"data": "old"}}, {"training": {"inputSha256": {"data": "old"}}}):
            path.read_text.return_value = json.dumps(saved)
            trainer.protect_existing_outputs(path, {}, {"data": "old"})
            with self.assertRaisesRegex(ValueError, "new --run-id"):
                trainer.protect_existing_outputs(path, {}, {"data": "new"})
        report, paths = trainer.output_paths("jordan_expansion_v2")
        self.assertNotEqual(report, trainer.REPORT)
        self.assertEqual(len(set(paths.values())), 3)
        for unsafe in ("../old", "", "UPPER", "x" * 41):
            with self.assertRaises(ValueError):
                trainer.output_paths(unsafe)


if __name__ == "__main__":
    unittest.main()
