"""Complete canonical result checks and source-bound browser/scorer integration."""
import json
import math
import subprocess
import unittest

from training.evaluation import behavior as evaluation
from training.corpus_io import sha256
from src.python.legacy_transaction_model import score_legacy_transaction_model
from src.python.engine import MasroofEngine
from tools.node_runtime import node_executable

ROOT = evaluation.ROOT
NODE = node_executable()


class RuntimeParityTests(unittest.TestCase):
    def test_legacy_head_math_and_inherited_property_words(self):
        cases = json.loads((ROOT / "tests/fixtures/legacy_model_score_cases.json").read_text(encoding="utf-8"))
        process = subprocess.run([NODE, str(ROOT / "tests/typescript/test_legacy_transaction_model.ts")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, 0, process.stderr)
        outputs = json.loads(process.stdout)
        for case, actual in zip(cases, outputs):
            model = case["model"]
            py = score_legacy_transaction_model(model["features"], case["tokens"], model["metadata"]["intercept_tx"], model["metadata"]["intercept_credit"])
            expected = [0 if case[key] < -710 else 1 / (1 + math.exp(-case[key])) for key in ("transactionLogit", "incomingLogit")]
            for x, y, z in zip(actual, py, expected):
                self.assertAlmostEqual(x, y, places=14)
                self.assertAlmostEqual(y, z, places=14)

    def test_bundle_sources_and_complete_python_ts_browser_results(self):
        _, _, _, cases = evaluation.load_inputs()
        cases += [{"id": "boundary:" + text, "input": {"text": text}}
                  for text in ("constructor", "__proto__", "constructor __proto__ JOD 12.50 mentioned in a conversation")]
        process = subprocess.run([NODE, str(ROOT / "tools/evaluation/probe_runtime.ts")], input=json.dumps({"cases": cases, "categoryProbes": []}),
                                 capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        self.assertEqual(process.returncode, 0, process.stderr)
        results = json.loads(process.stdout)
        self.assertTrue(results["bundledModelMatchesSource"])
        required = {"src/typescript/MasroofEngine.ts", "src/typescript/Preprocessing.ts", "src/typescript/ServiceNotice.ts", "src/typescript/LegacyTransactionModel.ts", "config/contracts/service_notice.json", "src/typescript/AuthorizationRequest.ts", "config/contracts/authorization_request.json"}
        self.assertTrue(required <= results["bundleSources"].keys())
        for relative, expected in results["bundleSources"].items():
            self.assertEqual(sha256(ROOT / relative), expected, relative)
        engine = MasroofEngine()
        for case, ts, web in zip(cases, results["typescript"], results["browser"]):
            item = case["input"]
            py = evaluation.canonical_result(engine.predict(item.get("sender") or "", item["text"], item.get("isContact", False)))
            self.assertNotIn("error", ts, case["id"])
            self.assertNotIn("error", web, case["id"])
            self.assertEqual(py, ts["result"], case["id"])
            self.assertEqual(py, web["result"], case["id"])


if __name__ == "__main__":
    unittest.main()
