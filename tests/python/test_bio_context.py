"""Cross-runtime research feature, schema, arithmetic and decoding contracts."""
import json
import subprocess
import unittest

from training.corpus_io import ROOT
from src.python.bio_sequence import TAGS
from src.python.bio_context import ContextBioModel, FEATURE_CONTRACT, sequence_features
from training.train_bio_context import fit


def model_with(weights):
    features = list(weights)
    return {"version": "2.0.0", "featureContract": FEATURE_CONTRACT, "tags": list(TAGS),
            "featureIndex": {feature: at for at, feature in enumerate(features)},
            "emissionWeights": [weights[feature].get(tag, 0.) for feature in features for tag in range(len(TAGS))],
            "transitionWeights": [0.] * len(TAGS) ** 2}


def probe(examples, model=None):
    return subprocess.run([r"C:\Program Files\nodejs\node.exe", str(ROOT / "tools/evaluation/probe_bio_context.ts")],
                          input=json.dumps({"examples": examples, "model": model}), capture_output=True, text=True, encoding="utf-8")


class BioContextTests(unittest.TestCase):
    def test_exact_feature_order_and_boundary_markers(self):
        self.assertEqual(sequence_features(["12.50"]), [["bias", "w0=<NUMBER>", "s0=number", "s0=digits:4", "s0=fraction:2",
                                                        "w-2=<BOS>", "w-1=<BOS>", "w1=<EOS>", "w2=<EOS>", "s-1=BOS", "s1=EOS"]])
        self.assertEqual(sequence_features([]), [])

    def test_unseen_numbers_and_scripts_share_features_without_raw_values(self):
        variants = [["خصم", "12.50", "رصيد", "80.00"], ["خَصْم", "١٢٫٥٠", "رَصيد", "٨٠٫٠٠"],
                    ["خصم", "۹۳٫۷۵", "رصيد", "۶۱٫۲۵"], ["خصم", "93.75", "رصيد", "61.25"]]
        expected = sequence_features(variants[0])
        for variant in variants:
            self.assertEqual(sequence_features(variant), expected)
        serialized = json.dumps(expected)
        self.assertNotIn("12.50", serialized)
        self.assertNotIn("93.75", serialized)
        self.assertEqual(sequence_features(["xxxx1234"]), sequence_features(["xxxx۹۸۷۶"]))

    def test_feature_vectors_match_typescript_for_numeric_and_unicode_boundaries(self):
        examples = [["Paid", "1,250.000", "JOD", "balance", "١٢٬٥٠٠٫٠٠٠"],
                    ["🧾", "أَسْوَاق", "*۱۲۳۴", "1234*678", "4’500", "1234567890", "", "__proto__", "constructor"],
                    ["-", "د.أ", "👨‍👩‍👦", "²", "Ⅷ", "café", "Π"], []]
        process = probe(examples)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["features"], [sequence_features(tokens) for tokens in examples])

    def test_context_disambiguates_equal_shape_unseen_amounts_and_balances(self):
        model = model_with({"w-1=paid": {1: 5.}, "w-1=balance": {9: 5.}})
        examples = [["Paid", "93.75", "balance", "61.25"], ["Paid", "۹۳٫۷۵", "balance", "۶۱٫۲۵"]]
        expected = [[0, 1, 0, 9]] * 2
        self.assertEqual([ContextBioModel(model).predict(tokens) for tokens in examples], expected)
        process = probe(examples, model)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["predictions"], expected)

    def test_illegal_iob_continuations_are_masked_before_argmax(self):
        model = model_with({"bias": {1: 2., 2: 10., 6: 20.}})
        # Highest raw score is I-MERCHANT, which is always illegal here.
        tokens = ["one", "two", "three"]
        self.assertEqual(ContextBioModel(model).predict(tokens), [1, 2, 2])
        process = probe([tokens], model)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["predictions"], [[1, 2, 2]])

    def test_float32_accumulation_and_ties_match_typescript(self):
        # 2**24 + 1 rounds back to 2**24; earliest tag then wins.
        model = model_with({"bias": {0: 16777216., 1: 16777216.}, "w0=word": {1: 1.}})
        tokens = ["word", "word"]
        self.assertEqual(ContextBioModel(model).predict(tokens), [0, 0])
        process = probe([tokens], model)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["predictions"], [[0, 0]])
        model = model_with({"bias": {0: 3e38, 1: 3e38}, "w0=word": {1: 3e38}})
        process = probe([tokens], model)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["predictions"], [ContextBioModel(model).predict(tokens)])

    def test_model_schema_rejection_matches_typescript(self):
        original = model_with({"bias": {0: 1.}})
        variants = [original | {"version": "1.0.0"}, original | {"featureContract": "other"},
                    original | {"tags": list(reversed(TAGS))}, original | {"transitionWeights": []},
                    original | {"featureIndex": {"bias": 0.5}}, original | {"featureIndex": {"bias": True}},
                    original | {"emissionWeights": ["1"] * len(TAGS)}, original | {"emissionWeights": [1e100] * len(TAGS)}]
        for bad in variants:
            with self.subTest(bad=str(bad)[:80]):
                with self.assertRaises(ValueError):
                    ContextBioModel(bad)
                self.assertNotEqual(probe([["test"]], bad).returncode, 0)

    def test_fitting_uses_only_provided_training_rows(self):
        rows = [{"tokens": ["paid", "12.50", "balance", "80.00"], "tags": ["O", "B-AMT", "O", "B-BAL"]}]
        model = fit(rows)
        self.assertEqual(model["metadata"]["trainingCount"], 1)
        self.assertEqual(model["metadata"]["epochs"], 25)
        self.assertFalse(any("12.50" in feature or "80.00" in feature or "unseen-only" in feature for feature in model["featureIndex"]))
        self.assertEqual(ContextBioModel(model).predict(["paid", "93.75", "balance", "61.25"]), [0, 1, 0, 9])


if __name__ == "__main__":
    unittest.main()
