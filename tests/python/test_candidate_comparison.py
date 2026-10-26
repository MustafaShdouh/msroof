"""Candidate score/export contracts and identical-guard research comparisons."""
from collections import Counter
import importlib.util
import json
import subprocess
import unittest
from unittest.mock import patch

from training.compare_transaction_candidate import CandidateEngine
from training.corpus_io import ROOT, sha256
from src.python.transaction_direction import evaluate_model, score_head
from src.python.verify_engine import MasroofEngine


class CandidateComparisonTests(unittest.TestCase):
    def test_shadow_heads_keep_lexical_direction_and_exclusion_guards(self):
        model = {"contractVersion": "1.0.0", "featureEncoding": "unigrams_then_adjacent_bigrams",
                 "transaction": {"intercept": 7, "threshold": .7, "weights": {}},
                 "direction": {"intercept": 7, "incomeThreshold": .5, "weights": {}}}
        active = ROOT / "data/models/masroof_model.json"
        before = sha256(active)
        engine = CandidateEngine(model)
        body = "You have a purchase transaction on account *6842 from SYNTHETIC SHOP amount JOD 12.500. Balance JOD 90.000."
        result = engine.predict("", body)
        self.assertTrue(result["isValidTransaction"])
        self.assertEqual(result["data"]["type"], "EXPENSE")
        self.assertEqual(result["data"]["amount"], 12.5)
        for sender, message, contact in (("", body, True), ("+962700000000", body, False),
                                         ("", "I just sent you 12.5 JOD", False),
                                         ("", "Transfer of JOD 12.5 between your own accounts completed.", False)):
            self.assertFalse(engine.predict(sender, message, contact)["isValidTransaction"], (sender, message, contact))
        self.assertEqual(sha256(active), before)
        model["transaction"]["threshold"] = .8
        with self.assertRaises(ValueError):
            CandidateEngine(model)

    def test_frozen_candidate_heads_match_typescript(self):
        features = [["purchase", "paid", "paid"], ["تم", "خصم", "تم خصم"], ["unknown", "constructor", "__proto__"]]
        for filename in ("transaction_direction_jordan_sanitized_v1_candidate.json", "transaction_direction_jordan_sanitized_liblinear_v1_candidate.json"):
            model = json.loads((ROOT / "data/models" / filename).read_text(encoding="utf-8"))
            process = subprocess.run([r"C:\Program Files\nodejs\node.exe", str(ROOT / "tools/evaluation/probe_candidate_heads.ts")],
                                     input=json.dumps({"model": model, "features": features}), capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(process.returncode, 0, process.stderr)
            actual = json.loads(process.stdout)
            for query, ts in zip(features, actual):
                py = evaluate_model(model, query)
                self.assertEqual(py.keys(), ts.keys())
                for field in py:
                    if type(py[field]) is float:
                        self.assertAlmostEqual(py[field], ts[field], places=12)
                    else:
                        self.assertEqual(py[field], ts[field])

    @unittest.skipUnless(importlib.util.find_spec("sklearn"), "Optional optimizer dependencies unavailable")
    def test_liblinear_export_matches_estimator_logits_without_hidden_scaling(self):
        from sklearn.linear_model import LogisticRegression
        from sklearn.feature_extraction import DictVectorizer
        from training import train_transaction_direction_v2 as trainer
        classifiers, vectorizers = [], []
        def classifier_factory(*args, **kwargs):
            classifier = LogisticRegression(*args, **kwargs)
            classifiers.append(classifier)
            return classifier
        def vectorizer_factory(*args, **kwargs):
            vectorizer = DictVectorizer(*args, **kwargs)
            vectorizers.append(vectorizer)
            return vectorizer
        examples = [(Counter(paid=2), 1), (Counter(paid=1, purchase=1), 1), (Counter(otp=1), 0), (Counter(message=1, otp=2), 0)]
        vocabulary = {"paid", "purchase", "otp", "message"}
        with patch.object(trainer, "OPTIMIZER", "liblinear"), patch("sklearn.linear_model.LogisticRegression", classifier_factory), patch("sklearn.feature_extraction.DictVectorizer", vectorizer_factory):
            intercept, weights = trainer._train_head(examples, vocabulary, 0)
        queries = [Counter(paid=3), Counter(otp=2, unseen=5), Counter(paid=1, otp=1)]
        direct = classifiers[0].decision_function(vectorizers[0].transform(queries))
        for query, expected in zip(queries, direct):
            tokens = list(query.elements())
            actual = score_head({"intercept": intercept, "weights": weights}, tokens)[0]
            self.assertAlmostEqual(actual, expected, places=12)


if __name__ == "__main__":
    unittest.main()
