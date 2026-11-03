"""Built tester UI parity with Python and verified embedding of immutable assets."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from src.python.research.sms_semantics import SmsSemanticsModel
from src.python.research.sms_completion_context import SmsCompletionContextModel
from tools.browser.sms_research import build_sms_research
from tools.node_runtime import node_executable
from training.corpus_io import ROOT


class SmsResearchTesterTests(unittest.TestCase):
    def test_built_page_display_matches_python_saved_export(self):
        process = subprocess.run([node_executable(), str(ROOT / "tests/typescript/test_sms_research_tester.ts")],
                                 capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        self.assertEqual(process.returncode, 0, process.stderr)
        results = json.loads(process.stdout)
        model = json.loads((ROOT / "data/models/sms_semantics_followup_v1_word_candidate.json").read_text(encoding="utf-8"))
        scorer = SmsSemanticsModel(model)
        for row in results["rows"]:
            heads = scorer.predict(row["text"])["heads"]
            self.assertEqual(row["displayed"]["completion"], {key: heads["completion"][key] for key in ("prediction", "score")})
            expected_direction = {key: heads["direction"][key] for key in ("prediction", "score")} if heads["completion"]["prediction"] == "completed" else None
            self.assertEqual(row["displayed"]["direction"], expected_direction)
        context = SmsCompletionContextModel(json.loads((ROOT / "data/models/sms_completion_context_v1_candidate.json").read_text(encoding="utf-8")))
        for row in results["contextRows"]:
            heads = context.predict(row["text"])["heads"]
            self.assertEqual(row["displayed"]["completion"], {key: heads["completion"][key] for key in ("prediction", "score")})
            direction = {key: heads["direction"][key] for key in ("prediction", "score")} if heads["completion"]["prediction"] == "completed" else None
            self.assertEqual(row["displayed"]["direction"], direction)

    def test_builder_refuses_changed_candidate_bytes_before_embedding(self):
        relative = "data/models/sms_semantics_followup_v1_word_candidate.json"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "data/reports/transactions/sms_semantics_followup_v1.json"
            report.parent.mkdir(parents=True)
            report.write_text(json.dumps({"outputSha256": {relative: "0" * 64}}), encoding="utf-8")
            model = root / relative
            model.parent.mkdir(parents=True)
            model.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "differs from frozen"):
                build_sms_research(root)


if __name__ == "__main__":
    unittest.main()
