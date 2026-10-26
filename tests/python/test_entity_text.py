"""Exact source names survive normalization and remain identical across runtimes."""
import json
import subprocess
import unittest
from src.python.entity_text import EntityText
from src.python.engine import MasroofEngine
from training.evaluation.behavior import ROOT, canonical_result
from tools.node_runtime import node_executable


class EntityTextTests(unittest.TestCase):
    def test_source_projection_preserves_original_name_and_rejects_invalid_spans(self):
        name = "أَسْوَاقِ  السَّلَامِ"
        source = "🧾\n" + name + "\t  JOD ١٢٫٥٠"
        view = EntityText(source)
        end = view.text.index(" JOD")
        start = view.text.index("أسواق")
        self.assertEqual(view.exact(start, end), name)
        self.assertIsNone(view.exact(-1, 3))
        self.assertIsNone(view.exact(0, 999))
        self.assertIsNone(view.exact(2, 2))

    def test_owning_name_policy_and_boundary_controls_match_ts(self):
        cases = json.loads((ROOT / "tests/fixtures/entity_text_cases.json").read_text(encoding="utf-8"))["cases"]
        engine = MasroofEngine()
        outputs = []
        for case in cases:
            with self.subTest(case=case["id"]):
                result = engine.predict("SERVICE", case["text"])
                self.assertTrue(result["isValidTransaction"])
                self.assertEqual(result["data"]["merchantOrParty"], case["name"])
                self.assertIn(result["data"]["merchantOrParty"], case["text"])
                outputs.append(canonical_result(result))
        process = subprocess.run([node_executable(), str(ROOT / "tests/typescript/test_entity_text.ts")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout), outputs)


if __name__ == "__main__":
    unittest.main()
