"""Research scorer, training provenance, leakage guards and exported-model parity."""

import copy
import json
import math
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from src.python import merchant_category as scorer
from training import train_merchant_category as trainer
from training.prepare_category_evaluation import prepare

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((ROOT / "tests/fixtures/merchant_category_contract.json").read_text(encoding="utf-8"))


class MerchantCategoryTests(unittest.TestCase):
    def test_fixed_normalization_features_and_logits(self):
        for case in FIXTURE["normalizationCases"]:
            self.assertEqual(scorer.normalize_name(case["raw"]), case["expected"])
        case = FIXTURE["scoreCase"]
        self.assertEqual(scorer.name_features(case["raw"]), case["expectedFeatures"])
        result = scorer.predict(scorer.load_model(FIXTURE["model"]), case["raw"])
        for actual, expected in zip(result["logits"], case["expectedLogits"]):
            self.assertAlmostEqual(actual, expected, places=12)
        self.assertEqual(result["category"], "Food")

    def test_no_evidence_and_sparse_class_abstention(self):
        for case in FIXTURE["abstentionCases"]:
            result = scorer.predict(scorer.load_model(FIXTURE["model"]), case["raw"])
            self.assertIsNone(result["category"])
            self.assertEqual(result["reason"], case["reason"])
        model = copy.deepcopy(FIXTURE["model"])
        model["classBusinessSupport"][0] = 1
        self.assertEqual(scorer.predict(scorer.load_model(model), 'A')["reason"], "insufficient_class_support")

    def test_bad_contract_dimensions_numbers_and_support_rejected(self):
        for change in ({"contractVersion": "unknown"}, {"classes": ["Food", "Food"]},
                       {"weights": [float('nan')] * 4}, {"weights": [0]},
                       {"classBusinessSupport": [True, 3]}, {"features": ["w:a", "c3:^a$"]}):
            with self.assertRaises(ValueError):
                scorer.load_model(FIXTURE["model"] | change)

    def corpus(self):
        rows = [{"businessId": str(i), "brandGroup": str(i), "name": f"Example Shop{i}",
                 "aliases": [f"Example-Shop{i}", f"إكزامبل {i}"], "labelStatus": "assistant_reviewed_merchant_default",
                 "humanConfirmedCategory": None, "assistantReviewedCategory": "Shopping"} for i in range(30)]
        return rows, prepare(rows)

    def test_augmentation_caps_provenance_and_equal_business_weight(self):
        rows, plan = self.corpus()
        for variant in trainer.VARIANTS:
            groups = trainer.training_views(rows, plan, variant)
            self.assertEqual(len(groups), sum(fold == "train" for fold in plan["businessAssignments"].values()))
            for views in groups:
                self.assertAlmostEqual(sum(view["businessWeight"] for view in views), 1)
                synthetic = [view for view in views if view["dataKind"] == "synthetic_name_perturbation"]
                self.assertLessEqual(len(synthetic), 1)
                self.assertTrue(all(view["labelReviewerType"] == "assistant" for view in views))
                self.assertEqual(len({tuple(scorer.name_features(view["text"])) for view in views}), len(views))

    def test_unknown_labels_and_holdouts_never_enter_training(self):
        rows, plan = self.corpus()
        unknown = next(row for row in rows if plan["businessAssignments"][row["businessId"]] == "train")
        unknown["labelStatus"] = "needs_review"
        groups = trainer.training_views(rows, plan, "augmented")
        self.assertNotIn(unknown["businessId"], {group[0]["businessId"] for group in groups})
        self.assertTrue(all(plan["businessAssignments"][group[0]["businessId"]] == "train" for group in groups))

    def test_generated_form_collision_with_holdout_rejected(self):
        rows, plan = self.corpus()
        source = next(row for row in rows if plan["businessAssignments"][row["businessId"]] == "train")
        heldout = next(row for row in rows if plan["businessAssignments"][row["businessId"]] == "test")
        heldout["name"] = trainer.synthetic_form(source["name"])[0]
        with self.assertRaisesRegex(ValueError, "collides with held-out"):
            trainer.training_views(rows, plan, "augmented")

    def test_weights_do_not_depend_on_heldout_labels_or_names(self):
        rows, plan = self.corpus()
        next(row for row in rows if plan["businessAssignments"][row["businessId"]] == "train")["assistantReviewedCategory"] = "Food"
        first = trainer.training_views(rows, plan, "baseline")
        for row in rows:
            if plan["businessAssignments"][row["businessId"]] != "train":
                row.update(name="HELDOUT UNIQUE SENTINEL", aliases=[], assistantReviewedCategory="Food")
        second = trainer.training_views(rows, plan, "baseline")
        self.assertEqual(first, second)
        with patch.object(trainer, "EPOCHS", 3):
            a = trainer.fit(first, ["Food", "Shopping"], "baseline", {})
            b = trainer.fit(second, ["Food", "Shopping"], "baseline", {})
        self.assertEqual(a, b)
        self.assertNotIn("w:sentinel", a["features"])
        self.assertEqual(sum(a["classBusinessSupport"]), len(first))
        self.assertTrue(any(value != 0 for value in a["weights"]))

    def test_selection_uses_human_validation_only_and_ties_keep_baseline(self):
        common = {"correctAnswered": 1, "wrongAnswered": 0}
        results = {name: {"humanLabelsOnly": dict(common), "assistantLabelsOnly": {"correctAnswered": 100 if name != "baseline" else 0}}
                   for name in trainer.VARIANTS}
        self.assertEqual(trainer.choose_variant(results), "baseline")
        results["augmented"]["humanLabelsOnly"]["correctAnswered"] = 2
        self.assertEqual(trainer.choose_variant(results), "augmented")
        results["augmented"]["humanLabelsOnly"]["wrongAnswered"] = 1
        self.assertEqual(trainer.choose_variant(results), "baseline")

    def test_test_inference_is_disabled(self):
        with self.assertRaisesRegex(ValueError, "Final test inference"):
            trainer.evaluate(FIXTURE["model"], [], {}, "test")

    def test_all_actual_exports_have_python_typescript_parity_without_test_inference(self):
        rows = [json.loads(line) for line in trainer.BUSINESSES.read_text(encoding="utf-8").splitlines()]
        plan = json.loads(trainer.SPLIT.read_text(encoding="utf-8"))
        texts = [case["raw"] for case in FIXTURE["normalizationCases"]]
        texts += sorted({name for row in rows if plan["businessAssignments"][row["businessId"]] != "test"
                         for name in [row["name"]] + row["aliases"]})
        extension_path = ROOT / "data/annotations/merchant_training_extension.jsonl"
        texts += [name for line in extension_path.read_text(encoding="utf-8").splitlines()
                  for row in [json.loads(line)] for name in [row["name"]] + row["aliases"]]
        texts += [name for row in json.loads((ROOT / "data/sources/businesses/jordan_training_round3.json").read_text(encoding="utf-8"))["businesses"]
                  for name in [row["name"]] + row["aliases"]]
        paths = [str(path.relative_to(ROOT)) for path in sorted((ROOT / "data/models").glob("merchant_category_research_*.json"))]
        process = subprocess.run([r"C:\Program Files\nodejs\node.exe", str(ROOT / "tests/typescript/test_merchant_category_contract.ts"), '--parity-input'],
                                 input=json.dumps({"models": paths, "texts": texts}), capture_output=True, text=True, encoding="utf-8", check=True)
        outputs = json.loads(process.stdout)
        for path, predictions in zip(paths, outputs):
            loaded = scorer.load_model(json.loads((ROOT / path).read_text(encoding="utf-8")))
            for text, actual in zip(texts, predictions):
                self.assertEqual(actual["normalized"], scorer.normalize_name(text))
                self.assertEqual(actual["features"], scorer.name_features(text))
                expected = scorer.predict(loaded, text)
                for key in ("category", "topClass", "reason"):
                    self.assertEqual(actual["prediction"][key], expected[key])
                for key in ("uncalibratedModelScore", "margin", "knownFeatureFraction"):
                    self.assertAlmostEqual(actual["prediction"][key], expected[key], places=10)
                for key in ("scores", "logits"):
                    for a, b in zip(actual["prediction"][key], expected[key]):
                        self.assertTrue(math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10))
        report = json.loads(trainer.REPORT.read_text(encoding="utf-8"))
        self.assertFalse(report["testInferencePerformed"])
        self.assertIsNone(report["testMetrics"])
        self.assertFalse(report["runtimePromotionAllowed"])


if __name__ == "__main__":
    unittest.main()
